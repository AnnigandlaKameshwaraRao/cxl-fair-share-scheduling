// BTP: FR-FCFS per-bank transaction queue for SST memHierarchy's timingDRAM backend.
//
// Drop-in replacement for memHierarchy.fifoTransactionQ, selected per run with
//   channel.rank.bank.transactionQ = "btpmem.frfcfsTransactionQ"
// It should be paired with an open page policy
//   channel.rank.bank.pagePolicy.close = 0
// because the default closed policy precharges the row before every pop, which leaves
// no open row to hit.
//
// Policy (Rixner et al., ISCA 2000): among this bank's queued transactions, serve the
// oldest one whose row equals the bank's open row; if none, serve the oldest.
// With the per-host front end on (btpmem.timingDRAM "arb") and host priority at the bank level, the
// order is: best host rank first, then row hit, then oldest. With all ranks equal this is exactly the
// FR-FCFS order above.
// Optional starvation cap ("maxRowHits", 0 = off): after that many row hits served in a
// row while an older transaction waits, the oldest is served next (gem5's MemCtrl uses
// max_accesses_per_row = 16 for the same purpose).
//
// Built against the sst-elements 14.0.0 header timingTransaction.h, unchanged, so the
// TransactionQ base class is identical to the one inside libmemHierarchy.so.

#include <sst/core/sst_config.h>
#include "sst/elements/memHierarchy/memTypes.h"   // Addr
#include "timingTransaction.h"
#include "btpArb.h"
#include <algorithm>

namespace SST {
namespace BTP {

using SST::MemHierarchy::TimingDRAM_NS::Transaction;
using SST::MemHierarchy::TimingDRAM_NS::TransactionQ;

class FrfcfsTransactionQ : public TransactionQ {
  public:
    SST_ELI_REGISTER_SUBCOMPONENT(FrfcfsTransactionQ, "btpmem", "frfcfsTransactionQ", SST_ELI_ELEMENT_VERSION(1,0,0),
            "FR-FCFS transaction queue: oldest open-row hit first, else oldest; optional row-hit cap",
            SST::MemHierarchy::TimingDRAM_NS::TransactionQ)

    SST_ELI_DOCUMENT_PARAMS(
        {"maxRowHits", "Serve the oldest after this many consecutive row hits that bypassed it (0 = no cap)", "0"} )

    SST_ELI_DOCUMENT_STATISTICS(
        {"rowHitPops",   "Pops that served a transaction to the open row", "count", 1},
        {"bypassPops",   "Row-hit pops that bypassed an older transaction", "count", 1},
        {"capPops",      "Pops forced to the oldest by the row-hit cap", "count", 1},
        {"totalPops",    "All pops", "count", 1} )

    FrfcfsTransactionQ( ComponentId_t id, Params& params ) : TransactionQ( id, params ), m_streak(0) {
        m_maxRowHits = params.find<unsigned>("maxRowHits", 0);
        s_rowHit = registerStatistic<uint64_t>("rowHitPops");
        s_bypass = registerStatistic<uint64_t>("bypassPops");
        s_cap    = registerStatistic<uint64_t>("capPops");
        s_total  = registerStatistic<uint64_t>("totalPops");
        SST::BTP::arbState().queues.push_back( &m_transQ );   // BTP: for PAR-BS batch marking
    }

    // row = the bank's open row, or (unsigned)-1 when the bank is precharged
    Transaction* pop( unsigned row ) override {
        if ( m_transQ.empty() ) return nullptr;
        s_total->addData(1);

        SST::BTP::ArbState& arb = SST::BTP::arbState();
        bool ranked = arb.on && arb.bankLevel;
        auto hostOf = [&]( Transaction* t ) { return arb.hostOf( t->addr ); };
        auto rankOf = [&]( Transaction* t ) { return arb.rank[ arb.hostOf( t->addr ) ]; };

        if ( ranked && arb.bankOrder == SST::BTP::BankOrder::MARK_ROWHIT_RANK_AGE ) {
            // PAR-BS: batch first, then row hit, then host rank, then oldest
            auto pick = m_transQ.begin();
            int bestKey[3] = { 2, 2, 0 };
            bool first = true;
            for ( auto it = m_transQ.begin(); it != m_transQ.end(); ++it ) {
                int k[3] = { arb.marked.count( *it ) ? 0 : 1, ( row != (unsigned)-1 && (*it)->row == row ) ? 0 : 1, rankOf( *it ) };
                if ( first || std::lexicographical_compare( k, k + 3, bestKey, bestKey + 3 ) ) {
                    std::copy( k, k + 3, bestKey ); pick = it; first = false;
                }
            }
            Transaction* trans = *pick;
            m_transQ.erase( pick );
            arb.marked.erase( trans );
            return finishPop( trans, row );
        }

        // ATLAS over-threshold rule: the oldest request older than the threshold goes first
        if ( ranked && arb.overThresh ) {
            auto over = m_transQ.end();
            uint64_t oldestArrive = 0;
            for ( auto it = m_transQ.begin(); it != m_transQ.end(); ++it ) {
                auto f = arb.arriveOf.find( (*it)->id );
                if ( f == arb.arriveOf.end() || arb.now - f->second <= arb.overThresh ) continue;
                if ( over == m_transQ.end() || f->second < oldestArrive ) { over = it; oldestArrive = f->second; }
            }
            if ( over != m_transQ.end() ) {
                Transaction* trans = *over;
                m_transQ.erase( over );
                m_streak = 0;
                arb.overPicks[ hostOf( trans ) ]++;
                return finishPop( trans, row );
            }
        }

        // SAA run cap: once one host has had runCap picks in a row here and another host waits,
        // that host's requests sit out this pick
        int excl = -1;
        if ( ranked && arb.runCap && m_runHost >= 0 && m_runLen >= arb.runCap ) {
            for ( Transaction* t : m_transQ ) if ( (int)hostOf( t ) != m_runHost ) { excl = m_runHost; break; }
        }
        auto eligible = [&]( Transaction* t ) { return excl < 0 || (int)hostOf( t ) != excl; };

        // oldest = the oldest eligible request of the best-ranked host present (the plain oldest without ranks)
        auto oldest = m_transQ.begin();
        int bestRank = 0;
        if ( ranked ) {
            oldest = m_transQ.end();
            for ( auto it = m_transQ.begin(); it != m_transQ.end(); ++it ) {
                if ( ! eligible( *it ) ) continue;
                int r = rankOf( *it );
                if ( oldest == m_transQ.end() || r < bestRank ) { bestRank = r; oldest = it; }
            }
        }

        auto pick = m_transQ.end();
        if ( row != (unsigned)-1 ) {
            for ( auto it = m_transQ.begin(); it != m_transQ.end(); ++it ) {   // list is in arrival order
                if ( (*it)->row != row ) continue;
                if ( ranked && ( ! eligible( *it ) || rankOf( *it ) != bestRank ) ) continue;
                pick = it;
                break;
            }
        }

        bool bypass = ( pick != m_transQ.end() && pick != oldest );
        if ( bypass && m_maxRowHits && m_streak >= m_maxRowHits ) {
            pick = m_transQ.end();          // cap reached: serve the oldest
            s_cap->addData(1);
        }

        Transaction* trans;
        if ( pick == m_transQ.end() ) {
            trans = *oldest;
            m_transQ.erase( oldest );
            m_streak = 0;
        } else {
            trans = *pick;
            m_transQ.erase( pick );
            m_streak = bypass ? m_streak + 1 : 0;
            if ( bypass ) s_bypass->addData(1);
        }
        if ( excl >= 0 ) m_runCuts++;
        return finishPop( trans, row );
    }

    // counters and scheduler hook for every pop
    Transaction* finishPop( Transaction* trans, unsigned row ) {
        SST::BTP::ArbState& arb = SST::BTP::arbState();
        if ( row != (unsigned)-1 && trans->row == row ) s_rowHit->addData(1);
        if ( arb.on ) {
            unsigned h = arb.hostOf( trans->addr );
            arb.bankPops[h]++;
            if ( row != (unsigned)-1 && trans->row == row ) arb.bankRowHits[h]++;
            if ( (int)h == m_runHost ) m_runLen++;
            else { m_runHost = h; m_runLen = 1; }
            if ( arb.sched ) arb.sched->onPick( h, row, trans->row );
        }
        return trans;
    }

  private:
    int      m_runHost = -1;    // BTP: host of the last pick and how many picks in a row it had
    unsigned m_runLen = 0;
    uint64_t m_runCuts = 0;
    unsigned m_maxRowHits;
    unsigned m_streak;          // consecutive row hits that bypassed an older transaction
    Statistic<uint64_t>* s_rowHit;
    Statistic<uint64_t>* s_bypass;
    Statistic<uint64_t>* s_cap;
    Statistic<uint64_t>* s_total;
};

}
}
