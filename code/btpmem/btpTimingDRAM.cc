// BTP copy of sst-elements 14.0.0 memHierarchy/membackend/timingDRAMBackend.cc, registered as
// btpmem.timingDRAM; changes are marked "BTP" (lazyPop option and command counters).
//
// Copyright 2009-2024 NTESS. Under the terms
// of Contract DE-NA0003525 with NTESS, the U.S.
// Government retains certain rights in this software.
//
// Copyright (c) 2009-2024, NTESS
// All rights reserved.
//
// This file is part of the SST software package. For license
// information, see the LICENSE file in the top level directory of the
// distribution.


#include <sst_config.h>
#include <sst/core/timeLord.h>
#include "btpTimingDRAM.h"

using namespace SST;
using namespace SST::MemHierarchy;

bool BtpTimingDRAM::m_printConfig = true;
bool BtpTimingDRAM::Channel::m_printConfig = true;
bool BtpTimingDRAM::Rank::m_printConfig = true;
bool BtpTimingDRAM::Bank::m_printConfig = true;
uint64_t BtpTimingDRAM::s_numPRE = 0;
uint64_t BtpTimingDRAM::s_numACT = 0;
uint64_t BtpTimingDRAM::s_numCOL = 0;

SST::BTP::ArbState& SST::BTP::arbState() { static ArbState s; return s; }

void BtpTimingDRAM::finish()
{
    // row hits = column commands that needed no activate
    printf("BTP_ROWSTATS PRE=%" PRIu64 " ACT=%" PRIu64 " COL=%" PRIu64 " rowhit=%.4f\n",
           s_numPRE, s_numACT, s_numCOL, s_numCOL ? 1.0 - (double)s_numACT / s_numCOL : 0.0);
    if ( m_arb ) {
        BTP::ArbState& a = BTP::arbState();
        if ( a.sched ) a.sched->finish();
        printf("BTP_ARB scheduler=%s level=%s hosts=%u channels=%zu cycles=%" PRIu64 "\n",
               m_sched.c_str(), m_level.c_str(), m_numHosts, m_channels.size(), (uint64_t)m_cycle);
        for ( unsigned h = 0; h < m_numHosts; h++ ) {
            double n = a.served[h] ? (double)a.served[h] : 1.0;
            printf("BTP_ARB_HOST host=%u rank=%d admitted=%" PRIu64 " served=%" PRIu64
                   " mean_wait=%.2f mean_dev_latency=%.2f mean_slot_interf=%.2f mean_bank_interf=%.2f"
                   " bank_pops=%" PRIu64 " rowhit=%.4f max_queue=%" PRIu64 "\n",
                   h, a.rank[h], a.admitted[h], a.served[h],
                   a.admitted[h] ? (double)a.waitCycles[h] / a.admitted[h] : 0.0,
                   a.devLatency[h] / n, a.slotInterf[h] / n, a.bankInterf[h] / n,
                   a.bankPops[h], a.bankPops[h] ? (double)a.bankRowHits[h] / a.bankPops[h] : 0.0, a.maxQueue[h]);
        }
    }
}

BtpTimingDRAM::BtpTimingDRAM(ComponentId_t id, Params &params) : SimpleMemBackend(id, params), m_cycle(0), m_seq(0) {

    int dram_id = params.find<int>("id", -1);
    assert( dram_id != -1 );

    std::ostringstream tmp;
    tmp << "@t:BtpTimingDRAM::@p():@l:mc=" << dram_id << ": ";

    int dbg_level = params.find<int>("dbg_level", 1);
    int dbg_mask = params.find<int>("dbg_mask", -1);
    output = new Output(tmp.str().c_str(), dbg_level, dbg_mask, Output::STDOUT);

    std::string addrMapper = params.find<std::string>("addrMapper","memHierarchy.simpleAddrMapper");

    Params tmpParams = params.get_scoped_params("addrMapper" );
    m_mapper = loadModule<AddrMapper>( addrMapper, tmpParams );

    if ( ! m_mapper ) {
        output->fatal(CALL_INFO, -1, "Invalid param(%s): addrMapper,  '%s'.\n",
            getName().c_str(), addrMapper.c_str());
    }

    int numChannels = params.find<int>("channels", 1);

    if (m_printConfig)
        m_printConfig = params.find<bool>("printconfig", true);
    if ( m_printConfig ) {
        output->verbose(CALL_INFO, 1, DBG_MASK, "number of channels: %d\n",numChannels);
        output->verbose(CALL_INFO, 1, DBG_MASK, "address mapper:     %s\n",addrMapper.c_str());
        m_printConfig = false;
    }

    m_mapper->setNumChannels( numChannels );

    // BTP per-host front end: set up before the channels so the banks know whether to track hosts
    m_arb = params.find<bool>("arb", false);
    Params arbParams = params.get_scoped_params("arb");
    m_sched    = arbParams.find<std::string>("scheduler", "frfcfs");
    m_level    = arbParams.find<std::string>("level", "both");
    m_numHosts = arbParams.find<unsigned>("num_hosts", 4);
    BTP::ArbState& a = BTP::arbState();
    a.on = m_arb;
    a.hostShift = arbParams.find<unsigned>("host_shift", 30);
    if ( m_numHosts == 0 ) {
        output->fatal(CALL_INFO, -1, "btpmem.timingDRAM: arb.num_hosts must be at least 1\n");
    }
    a.init( m_numHosts );
    a.numChannels = numChannels;
    a.tCL   = params.find<unsigned>("channel.rank.bank.CL", 11);
    a.tRCD  = params.find<unsigned>("channel.rank.bank.RCD", 11);
    a.tRP   = params.find<unsigned>("channel.rank.bank.TRP", 11);
    a.tData = params.find<unsigned>("channel.rank.bank.dataCycles", 4);
    if ( m_arb ) {
        if ( m_level == "both" )       { a.admitLevel = true;  a.bankLevel = true; }
        else if ( m_level == "admit" ) { a.admitLevel = true;  a.bankLevel = false; }
        else if ( m_level == "bank" )  { a.admitLevel = false; a.bankLevel = true; }
        else output->fatal(CALL_INFO, -1, "btpmem.timingDRAM: arb.level '%s' must be both, admit or bank\n", m_level.c_str());

        if ( m_sched == "fcfs" || m_sched == "frfcfs" ) {
            // no host priority: every rank stays 0
        } else if ( m_sched == "static" ) {
            std::string r = arbParams.find<std::string>("ranks", "");
            std::stringstream ss( r );
            std::string tok;
            unsigned h = 0;
            while ( std::getline( ss, tok, ',' ) ) {
                if ( h >= m_numHosts ) output->fatal(CALL_INFO, -1, "btpmem.timingDRAM: arb.ranks has more than %u entries\n", m_numHosts);
                a.rank[h++] = std::stoi( tok );
            }
            if ( h != m_numHosts ) output->fatal(CALL_INFO, -1, "btpmem.timingDRAM: arb.ranks needs %u entries, got '%s'\n", m_numHosts, r.c_str());
        } else {
            a.sched = BTP::makeHostSched( m_sched, arbParams );
            if ( ! a.sched )
                output->fatal(CALL_INFO, -1, "btpmem.timingDRAM: arb.scheduler '%s' is not known (fcfs, frfcfs, static, bliss, atlas, tcm, parbs, saa)\n", m_sched.c_str());
            printf("BTP_ARB settings: %s\n", a.sched->describe().c_str());
        }
        m_hostQ.assign( numChannels, std::vector<std::deque<ArbReq>>( m_numHosts ) );
        m_hostPend.assign( numChannels, std::vector<unsigned>( m_numHosts, 0 ) );
        std::string rs;
        for ( unsigned h = 0; h < m_numHosts; h++ ) rs += ( h ? "," : "" ) + std::to_string( a.rank[h] );
        printf("BTP_ARB on: scheduler=%s level=%s hosts=%u host_shift=%u channels=%d ranks=%s\n",
               m_sched.c_str(), m_level.c_str(), m_numHosts, a.hostShift, numChannels, rs.c_str());
    }

    tmpParams = params.get_scoped_params("channel" );
    for ( unsigned i=0; i < numChannels; i++ ) {
        using std::placeholders::_1;
        m_channels.push_back(loadComponentExtension<Channel>( std::bind(&BtpTimingDRAM::handleResponse, this, _1), tmpParams, dram_id, i, output, m_mapper ));
    }

}

// BTP: the per-host arbiter of one channel. Moves requests from the host queues of this channel into the
// channel's pending slots until the slots are full or the queues are empty. fcfs/frfcfs: oldest request
// across hosts first, which on one channel is exactly the stock front end's arrival order.
void BtpTimingDRAM::admit( unsigned chan )
{
    BTP::ArbState& a = BTP::arbState();
    std::vector<std::deque<ArbReq>>& q = m_hostQ[chan];
    std::vector<unsigned>& pend = m_hostPend[chan];
    std::vector<bool> waiting( m_numHosts );
    while ( true ) {
        // with host priority at admission: lowest key (host rank, or the scheduler's key) first,
        // then oldest; otherwise oldest
        bool anyWaiting = false;
        for ( unsigned h = 0; h < m_numHosts; h++ ) { waiting[h] = ! q[h].empty(); anyWaiting |= waiting[h]; }
        if ( ! anyWaiting ) return;
        unsigned slots = m_channels[chan]->getMaxPending(), pendTotal = m_channels[chan]->getPending();
        int best = -1, bestKey = 0;
        for ( unsigned h = 0; h < m_numHosts; h++ ) {
            if ( ! waiting[h] ) continue;
            if ( a.admitLevel && a.sched && ! a.sched->mayAdmit( h, chan, pend, pendTotal, slots, waiting ) ) continue;
            int key = ! a.admitLevel ? 0 : ( a.sched ? a.sched->admitKey( h, chan, pend ) : a.rank[h] );
            if ( a.overThresh && a.admitLevel && m_cycle - q[h].front().arrive > a.overThresh ) key = -1000000;
            if ( best < 0 || key < bestKey || ( key == bestKey && q[h].front().seq < q[best].front().seq ) ) {
                best = h; bestKey = key;
            }
        }

        if ( best < 0 || ! m_channels[chan]->issue( m_cycle, q[best].front().id, q[best].front().addr,
                                                     q[best].front().isWrite, q[best].front().numBytes ) ) {
            // channel full: every waiting request of a host is held up by the slots other hosts hold
            unsigned total = m_channels[chan]->getMaxPending();
            for ( unsigned h = 0; h < m_numHosts; h++ ) {
                if ( q[h].empty() ) continue;
                unsigned others = m_channels[chan]->getPending() - pend[h];
                a.slotInterf[h] += (double)q[h].size() * others / total;
            }
            return;   // this channel is full (or its free slots are reserved); the other channels are not affected
        }
        ArbReq& r = q[best].front();
        output->verbose(CALL_INFO, 2, DBG_MASK, "admit chan=%u host=%d reqId=%" PRIu64 " addr=%#" PRIx64 "\n",
                        chan, best, r.id, r.addr);
        a.admitted[best]++;
        if ( a.overThresh ) {
            a.arriveOf[r.id] = r.arrive;
            if ( a.admitLevel && m_cycle - r.arrive > a.overThresh ) a.overAdmits[best]++;
        }
        a.waitCycles[best] += m_cycle - r.arrive;
        pend[best]++;
        m_inFlight[r.id] = InFlight{ (unsigned)best, chan, r.arrive };
        q[best].pop_front();
    }
}

void BtpTimingDRAM::arbResponse( ReqId id )
{
    auto it = m_inFlight.find( id );
    if ( it == m_inFlight.end() ) return;
    BTP::ArbState& a = BTP::arbState();
    a.served[it->second.host]++;
    a.devLatency[it->second.host] += m_cycle - it->second.arrive;
    m_hostPend[it->second.chan][it->second.host]--;
    if ( a.overThresh ) a.arriveOf.erase( id );
    m_inFlight.erase( it );
}

bool BtpTimingDRAM::issueRequest( ReqId id, Addr addr, bool isWrite, unsigned numBytes )
{
    unsigned chan = m_mapper->getChannel(addr);

    if ( m_arb ) {
        // dispatcher: always accept, so the front end never stalls on a full channel
        unsigned host = hostOf( addr );
        std::deque<ArbReq>& q = m_hostQ[chan][host];
        q.push_back( ArbReq{ id, addr, isWrite, numBytes, m_seq++, m_cycle } );
        uint64_t& mq = BTP::arbState().maxQueue[host];
        if ( q.size() > mq ) mq = q.size();
        return true;
    }

    bool ret = m_channels[chan]->issue(m_cycle, id, addr, isWrite, numBytes );

    if ( ret ) {
        output->verbose(CALL_INFO, 2, DBG_MASK, "chan=%d reqId=%" PRIu64 " addr=%#" PRIx64 "\n",chan,id,addr);
    } else {
        output->verbose(CALL_INFO, 5, DBG_MASK, "chan=%d reqId=%" PRIu64 " addr=%#" PRIx64 " failed\n",chan,id,addr);
    }
    return ret;
}

bool BtpTimingDRAM::clock(Cycle_t cycle)
{
    output->verbose(CALL_INFO, 5, DBG_MASK, "cycle %" PRIu64 "\n",m_cycle);
    // BTP: admission happens before the channels clock, in the same cycle, as the stock front end's does
    if ( m_arb ) {
        BTP::ArbState& a = BTP::arbState();
        a.now = m_cycle;
        if ( a.sched ) a.sched->tick( m_cycle );
        for ( unsigned i = 0; i < m_channels.size(); i++ ) {
            admit( i );
        }
    }
    for ( unsigned i = 0; i < m_channels.size(); i++ ) {
        m_channels[i]->clock(m_cycle);
    }
    ++m_cycle;
    return false;
}

//==================================================================================
// Channel
//==================================================================================

BtpTimingDRAM::Channel::Channel( ComponentId_t id, std::function<void(ReqId)> handler, Params& params, unsigned mc, unsigned myNum, Output* output, AddrMapper* mapper ) :
    ComponentExtension(id), m_responseHandler(handler), m_output( output ), m_mapper( mapper ), m_nextRankUp(0), m_dataBusAvailCycle(0)
{
    std::ostringstream tmp;
    tmp << "@t:BtpTimingDRAM:Channel:@p():@l:mc=" << mc << ":chan=" << myNum << ": ";
    m_pre = tmp.str();

    unsigned numRanks = params.find<unsigned>("numRanks", 1);
    m_maxPendingTrans = params.find<unsigned>("transaction_Q_size", 32);

    m_pendingCount = 0;

    m_mapper->setNumRanks( numRanks );

    if (m_printConfig)
        m_printConfig = params.find<bool>("printconfig", true);
    if ( m_printConfig ) {
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "max pending trans: %d\n",m_maxPendingTrans);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "number of ranks:   %d\n",numRanks);
        m_printConfig = false;
    }

    Params tmpParams = params.get_scoped_params("rank" );
    for ( unsigned i=0; i<numRanks; i++ ) {
        m_ranks.push_back( loadComponentExtension<Rank>( tmpParams, mc, myNum, i, output, mapper ) );
    }
}

void BtpTimingDRAM::Channel::clock( SimTime_t cycle )
{
    if (is_debug)
        m_output->verbosePrefix(prefix(),CALL_INFO, 5, DBG_MASK, "cycle %" PRIu64 "\n",cycle);

    std::list<Cmd*>::iterator iter = m_issuedCmds.begin();

    /* Check all outstanding commands to see if anything is finished */
    while ( iter != m_issuedCmds.end() ) {
        if ( (*iter)->isDone(cycle) ) {
            Cmd* cmd = (*iter);

            if (is_debug)
                m_output->verbosePrefix(prefix(),CALL_INFO, 2, DBG_MASK, "cycle=%" PRIu64 " retire %s for rank=%d bank=%d row=%d\n",
                        cycle, cmd->getName().c_str(), cmd->getRank(), cmd->getBank(), cmd->getRow());

            if (cmd->getTrans() != nullptr) {
                cmd->getBankPtr()->release( cmd->getTrans(), cycle );   // BTP
                m_retiredTrans.push(cmd->getTrans());
            }

            delete (*iter);
            iter = m_issuedCmds.erase(iter);
        } else {
            ++iter;
        }
    }

    /* Return a response if possible */
    if ( ! m_retiredTrans.empty() ) {
        if (is_debug)
            m_output->verbosePrefix(prefix(),CALL_INFO, 3, DBG_MASK, "send response: reqId=%" PRIu64 " bank=%d addr=%#" PRIx64 ", createTime=%" PRIu64 "\n",
                    m_retiredTrans.front()->id, m_retiredTrans.front()->bank, m_retiredTrans.front()->addr, m_retiredTrans.front()->createTime);

        m_responseHandler(m_retiredTrans.front()->id);
        delete m_retiredTrans.front();

        m_retiredTrans.pop();
        m_pendingCount--;
    }

    /* For each rank, check if there's a command to issue */
    Cmd* cmd = popCmd( cycle, m_dataBusAvailCycle );
    if ( cmd ) {
        if (is_debug)
            m_output->verbosePrefix(prefix(),CALL_INFO, 2, DBG_MASK, "cycle=%" PRIu64 " issue %s for rank=%d bank=%d row=%d\n",
                    cycle, cmd->getName().c_str(), cmd->getRank(), cmd->getBank(), cmd->getRow());

        m_dataBusAvailCycle = cmd->issue();

        m_issuedCmds.push_back(cmd);
    }
}

BtpTimingDRAM::Cmd* BtpTimingDRAM::Channel::popCmd( SimTime_t cycle, SimTime_t dataBusAvailCycle )
{
    Cmd* cmd = nullptr;
    unsigned current = m_nextRankUp;
    for ( unsigned i = 0; i < m_ranks.size(); i++ ) {

        if (m_ranks[current]->hasActiveBanks()) {
            cmd = m_ranks[current]->popCmd( cycle, m_dataBusAvailCycle );

            if ( cmd ) {

                if ( current == m_nextRankUp ) {
                    ++m_nextRankUp;
                    m_nextRankUp %= m_ranks.size();
                    if (is_debug)
                        m_output->verbosePrefix(prefix(),CALL_INFO, 3, DBG_MASK, "rank %d next up\n",m_nextRankUp);
                }

                break;
            }
        }

        ++current;
        current %= m_ranks.size();
    }
    return cmd;
}

//==================================================================================
// Rank
//==================================================================================

BtpTimingDRAM::Rank::Rank( ComponentId_t id, Params& params, unsigned mc, unsigned chan, unsigned myNum, Output* output, AddrMapper* mapper ) :
    ComponentExtension(id), m_output( output ), m_mapper( mapper ), m_nextBankUp(0)
{
    std::ostringstream tmp;
    tmp << "@t:BtpTimingDRAM:Rank:@p():@l:mc=" << mc << ":chan=" << chan << ":rank=" << myNum <<": ";
    m_pre = tmp.str();

    int banks = params.find<int>("numBanks", 8);

    m_mapper->setNumBanks( banks );

    if (m_printConfig)
        m_printConfig = params.find<bool>("printconfig", true);
    if ( m_printConfig ) {
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "number of banks: %d\n",banks);
        m_printConfig = false;
    }

    Params tmpParams = params.get_scoped_params("bank" );
    for ( unsigned i=0; i<banks; i++ ) {
        m_banks.push_back( loadComponentExtension<Bank>( tmpParams, mc, chan, myNum, i, output ) );
    }
}

BtpTimingDRAM::Cmd* BtpTimingDRAM::Rank::popCmd( SimTime_t cycle, SimTime_t dataBusAvailCycle )
{
    if (is_debug)
        m_output->verbosePrefix(prefix(),CALL_INFO, 5, DBG_MASK, "\n" );

    unsigned current = m_nextBankUp;
    for ( unsigned i = 0; i < m_banks.size(); i++ ) {
        if (m_banksActive.find(current) != m_banksActive.end()) {
            Cmd* cmd = m_banks[current]->popCmd( cycle, dataBusAvailCycle );

            if (m_banks[current]->isIdle())
                m_banksActive.erase(current);

            if ( cmd ) {
                if ( current == m_nextBankUp ) {
                    ++m_nextBankUp;
                    m_nextBankUp %= m_banks.size();
                    if (is_debug)
                        m_output->verbosePrefix(prefix(),CALL_INFO, 3, DBG_MASK, "rank %d next up\n",m_nextBankUp);
                }
                return cmd;
            }
        }

        ++current;
        current %= m_banks.size();
    }
    return nullptr;
}

//==================================================================================
// Bank
//==================================================================================

BtpTimingDRAM::Bank::Bank( ComponentId_t id, Params& params, unsigned mc, unsigned chan, unsigned rank, unsigned myNum, Output* output ) :
    ComponentExtension(id), m_output( output ), m_lastCmd(nullptr), m_bank(myNum), m_rank(rank), m_row( -1 ),
    m_owner( -1 ), m_ownerTrans( nullptr ), m_lastT( 0 )
{
    m_track = BTP::arbState().on;   // BTP
    m_waiting.assign( BTP::arbState().numHosts, 0 );
    if ( m_track ) BTP::arbState().bankWaiting.push_back( &m_waiting );
    std::ostringstream tmp;
    tmp << "@t:BtpTimingDRAM:Bank:@p():@l:mc=" << mc << ":chan=" << chan << ":rank=" << rank << ":bank=" << myNum <<": ";
    m_pre = tmp.str();

    m_col_rd_lat = params.find<unsigned int>("CL", 11);
    m_col_wr_lat = params.find<unsigned int>("CL_WR", m_col_rd_lat);
    m_rcd_lat = params.find<unsigned int>("RCD", 11);
    m_trp_lat = params.find<unsigned int>("TRP", 11);
    m_data_lat = params.find<unsigned int>("dataCycles", 4);
    m_lazyPop = params.find<bool>("lazyPop", false);

    std::string name = params.find<std::string>("transactionQ", "memHierarchy.fifoTransactionQ");
    Params tmpParams = params.get_scoped_params("transactionQ" );
    m_transQ = loadAnonymousSubComponent<TransactionQ>(name, "transactionQ", 0, ComponentInfo::INSERT_STATS, tmpParams);

    std::string ppName = params.find<std::string>("pagePolicy", "memHierarchy.simplePagePolicy");
    tmpParams = params.get_scoped_params("pagePolicy" );
    m_pagePolicy = loadAnonymousSubComponent<PagePolicy>(ppName, "pagePolicy", 0, ComponentInfo::INSERT_STATS, tmpParams);

    if (m_printConfig)
        m_printConfig = params.find<bool>("printconfig", true);
    if ( m_printConfig ) {
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "CL:           %d\n",m_col_rd_lat);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "CL_WR:        %d\n",m_col_wr_lat);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "RCD:          %d\n",m_rcd_lat);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "TRP:          %d\n",m_trp_lat);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "dataCycles:   %d\n",m_data_lat);
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "transactionQ: %s\n",name.c_str());
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "pagePolicy:   %s\n",  ppName.c_str());
        m_output->verbosePrefix(prefix(),CALL_INFO, 1, DBG_MASK, "lazyPop:      %d\n",  (int)m_lazyPop);
        m_printConfig = false;
    }
}


BtpTimingDRAM::Cmd* BtpTimingDRAM::Bank::popCmd( SimTime_t cycle, SimTime_t dataBusAvailCycle )
{
    if (is_debug)
        m_output->verbosePrefix(prefix(),CALL_INFO, 4, DBG_MASK, "numCmds=%zu\n", m_cmdQ.size() );
    update( cycle );

    Cmd* cmd = nullptr;
    if ( ! m_cmdQ.empty() && m_cmdQ.front()->canIssue( cycle, dataBusAvailCycle ) ) {
        cmd = m_cmdQ.front();
        if (is_debug)
            m_output->verbosePrefix(prefix(),CALL_INFO, 2, DBG_MASK, "%s row=%d\n",cmd->getName().c_str(), cmd->getRow() );
        m_cmdQ.pop_front();
    }
    return cmd;
}

void BtpTimingDRAM::Bank::update( SimTime_t current )
{
    if ( nullptr == m_lastCmd && m_row != -1 && m_pagePolicy->shouldClose( current ) ) {
        Cmd* cmd = new Cmd( this, Cmd::PRE, m_trp_lat );
        m_cmdQ.push_back(cmd);
        ++s_numPRE;
        m_row = -1;
        return;
    }

    // BTP: with lazyPop the queue policy chooses only when the bank has nothing left to issue
    if ( m_lazyPop && ! m_cmdQ.empty() ) {
        return;
    }

    Transaction* trans = m_transQ->pop(m_row);

    if ( ! trans ) {
        return;
    }

    if ( m_track ) {   // BTP: the bank now serves this request's host
        accrue( current );
        unsigned h = BTP::arbState().hostOf( trans->addr );
        m_waiting[h]--;
        m_owner = h;
        m_ownerTrans = trans;
    }

    if (is_debug)
        m_output->verbosePrefix(prefix(),CALL_INFO, 2, DBG_MASK, "addr=%#" PRIx64 " current row=%d trans row=%d, time=%" PRIu64 "\n",
                trans->addr, m_row, trans->row, trans->createTime );

    Cmd* cmd;

    if ( trans->row != m_row ) {
        if ( m_row != -1 ) {
            cmd = new Cmd( this, Cmd::PRE, m_trp_lat );
            m_cmdQ.push_back(cmd);
            ++s_numPRE;
        }

        cmd = new Cmd( this, Cmd::ACT, m_rcd_lat, trans->row );
        m_cmdQ.push_back(cmd);
        ++s_numACT;
        m_row = trans->row;
    }

    unsigned val = trans->isWrite ? m_col_wr_lat :  m_col_rd_lat;
    cmd = new Cmd( this, Cmd::COL, val, trans->row, m_data_lat, trans );
    m_cmdQ.push_back(cmd);
    ++s_numCOL;
}
