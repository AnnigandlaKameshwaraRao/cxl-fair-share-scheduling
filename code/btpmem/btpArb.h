// BTP: state shared by the per-host front end (btpmem.timingDRAM "arb"), the bank queues
// (btpmem.frfcfsTransactionQ) and the host schedulers (btpSched.cc): the host ranking, the
// per-host counters and the scheduler hooks. One pool backend per simulation, so one instance
// (arbState()).
#ifndef _H_BTP_ARB
#define _H_BTP_ARB

#include <vector>
#include <list>
#include <string>
#include <cstdint>
#include <unordered_set>
#include <unordered_map>
#include <sst/core/params.h>
#include "sst/elements/memHierarchy/memTypes.h"   // Addr
#include "timingTransaction.h"

namespace SST {
namespace BTP {

using SST::MemHierarchy::TimingDRAM_NS::Transaction;

class HostSched;

// How a bank queue orders its requests when the front end is on and host priority acts at the bank
enum class BankOrder {
    RANK_ROWHIT_AGE,     // host rank, then row hit, then oldest (FR-FCFS when all ranks are equal)
    MARK_ROWHIT_RANK_AGE // PAR-BS: requests of the current batch, then row hit, then host rank, then oldest
};

struct ArbState {
    bool     on         = false;  // per-host front end active
    unsigned numHosts   = 1;
    unsigned numChannels = 1;
    unsigned hostShift  = 30;     // host = (addr >> hostShift) % numHosts
    bool     admitLevel = true;   // host priority used when filling a channel's pending slots
    bool     bankLevel  = true;   // host priority used when a bank picks its next request
    BankOrder bankOrder = BankOrder::RANK_ROWHIT_AGE;
    unsigned runCap     = 0;      // SAA: cut a host's run of row hits in a bank after this many
                                  // while another host waits on that bank (0 = off)
    uint64_t now        = 0;      // current pool cycle

    // DRAM timing of a bank (pool cycles), for schedulers that count service time
    unsigned tCL = 11, tRCD = 11, tRP = 14, tData = 4;

    // Host ranking: lower value is served first. All equal = no host priority (plain FR-FCFS/FCFS).
    std::vector<int> rank;

    HostSched* sched = nullptr;   // null for fcfs/frfcfs/static

    // Registries filled at construction: every FR-FCFS bank queue's list and every bank's
    // per-host waiting counts (for PAR-BS marking and TCM's bank-level parallelism)
    std::vector<std::list<Transaction*>*>   queues;
    std::vector<const std::vector<uint64_t>*> bankWaiting;

    // PAR-BS: requests in the current batch
    std::unordered_set<Transaction*> marked;

    // ATLAS over-threshold rule: a request older than overThresh pool cycles (since it reached the device)
    // goes first, before any host rank, at admission and at the bank (0 = off). arriveOf holds the arrival
    // cycle of every admitted request while the rule is on.
    uint64_t overThresh = 0;
    std::unordered_map<uint64_t, uint64_t> arriveOf;
    std::vector<uint64_t> overAdmits, overPicks;   // per host: admissions and bank picks made by the rule

    // Per-host counters over the whole run (cycles are pool cycles, 1.2 GHz)
    std::vector<uint64_t> admitted;     // requests moved into a pending slot
    std::vector<uint64_t> waitCycles;   // arrival at the device to admission into a slot
    std::vector<uint64_t> maxQueue;     // largest per-host queue (over channels) seen
    std::vector<uint64_t> served;       // responses returned
    std::vector<uint64_t> devLatency;   // arrival at the device to response, summed
    std::vector<double>   slotInterf;   // request-cycles waiting for a slot while the channel was full,
                                        // weighted by the share of slots held by other hosts
    std::vector<uint64_t> bankInterf;   // request-cycles waiting in a bank queue while that bank
                                        // was serving another host's request
    std::vector<uint64_t> bankPops;     // requests a bank queue picked (FR-FCFS queue only)
    std::vector<uint64_t> bankRowHits;  // of which hit the open row

    void init( unsigned n ) {
        numHosts = n;
        rank.assign( n, 0 );
        admitted.assign( n, 0 );   waitCycles.assign( n, 0 ); maxQueue.assign( n, 0 );
        served.assign( n, 0 );     devLatency.assign( n, 0 ); slotInterf.assign( n, 0.0 );
        bankInterf.assign( n, 0 ); bankPops.assign( n, 0 );   bankRowHits.assign( n, 0 );
        overAdmits.assign( n, 0 ); overPicks.assign( n, 0 );
    }
    unsigned hostOf( SST::MemHierarchy::Addr a ) const { return ( a >> hostShift ) % numHosts; }

    // service cycles of one request in a bank: open-row hit, closed bank, or row conflict
    unsigned serviceCycles( unsigned openRow, unsigned row ) const {
        if ( openRow == (unsigned)-1 ) return tRCD + tCL + tData;
        if ( openRow == row ) return tCL + tData;
        return tRP + tRCD + tCL + tData;
    }
};

ArbState& arbState();   // defined in btpTimingDRAM.cc

// A host scheduler: keeps arbState().rank up to date and may add admission rules.
class HostSched {
  public:
    virtual ~HostSched() {}
    // once per pool cycle, before admission
    virtual void tick( uint64_t now ) {}
    // a bank queue picked a request of this host (openRow = the bank's open row before the pick)
    virtual void onPick( unsigned host, unsigned openRow, unsigned row ) {}
    // admission: lower key is admitted first (ties: oldest); default = host rank
    virtual int admitKey( unsigned host, unsigned chan, const std::vector<unsigned>& pend ) {
        return arbState().rank[host];
    }
    // admission: may this host take a free slot now?
    virtual bool mayAdmit( unsigned host, unsigned chan, const std::vector<unsigned>& pend,
                           unsigned pendTotal, unsigned slots, const std::vector<bool>& waiting ) {
        return true;
    }
    virtual void finish() {}
    virtual std::string describe() = 0;
};

// Builds the scheduler named by arb.scheduler, or returns null for fcfs/frfcfs/static
HostSched* makeHostSched( const std::string& name, SST::Params& params );

}
}

#endif
