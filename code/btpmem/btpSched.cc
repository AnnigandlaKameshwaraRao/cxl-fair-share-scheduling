// BTP: host schedulers for the per-host front end of the pool (btpmem.timingDRAM "arb").
// Each one keeps arbState().rank up to date (lower = served first); the channel arbiter admits
// by rank and the FR-FCFS bank queues pick by rank, then row hit, then age (PAR-BS: batch first).
// A "host" here is what the papers call a thread. All counts are pool cycles (1.2 GHz).
//
//   bliss  Subramanian et al., ICCD 2014: blacklist a host served more than `threshold` times in a
//          row; blacklisted hosts go behind the others until the list is cleared every
//          `clear_interval` cycles. One counter for the whole pool.
//   atlas  Kim et al., HPCA 2010: least attained service first. Attained service = bank service
//          cycles; at the end of each `quantum`, total = alpha * total + (1 - alpha) * this quantum's.
//          Over-threshold rule as in the paper: a request older than `threshold` cycles goes first.
//   tcm    Kim et al., MICRO 2010: every `quantum`, hosts are split by bandwidth use (bank service
//          cycles, standing in for misses per kilo-instruction, which only the core knows): the
//          lightest hosts whose summed use stays within `cluster_thresh` of the total form the
//          latency-sensitive cluster, served first, lightest first. The rest are ordered by
//          niceness (bank-level parallelism rank minus row-hit-rate rank) and that order is rotated
//          by one every `shuffle_interval` cycles (the paper's insertion shuffle is simplified to a
//          rotation).
//   parbs  Mutlu and Moscibroda, ISCA 2008: when no batch request is left, mark up to `cap` oldest
//          requests per host in every bank queue; batch requests first, then row hit, then host
//          rank (fewest marked requests in its busiest bank, then fewest in total), then oldest.
//   saa    ours: rank hosts by an estimated slowdown, highest first, with reserved pending slots, a
//          light-host guard and a cap on one host's run of picks in a bank.
//          See docs/12_scheduler_design.md.

#include <sst/core/sst_config.h>
#include <algorithm>
#include <numeric>
#include <cstdio>
#include <cmath>
#include "btpArb.h"

namespace SST {
namespace BTP {

static void ranksByKey( const std::vector<double>& key, bool ascending ) {
    // rank[h] = position of h when sorted by key (ties by host number)
    ArbState& a = arbState();
    std::vector<unsigned> order( a.numHosts );
    std::iota( order.begin(), order.end(), 0 );
    std::stable_sort( order.begin(), order.end(), [&]( unsigned x, unsigned y ) {
        return ascending ? key[x] < key[y] : key[x] > key[y];
    });
    for ( unsigned i = 0; i < order.size(); i++ ) a.rank[ order[i] ] = i;
}

static std::string ranksString() {
    ArbState& a = arbState();
    std::string s;
    for ( unsigned h = 0; h < a.numHosts; h++ ) s += ( h ? "," : "" ) + std::to_string( a.rank[h] );
    return s;
}

//------------------------------------------------------------------------------------------------
class Bliss : public HostSched {
  public:
    Bliss( Params& p ) {
        m_thresh = p.find<unsigned>( "threshold", 4 );
        m_clear  = p.find<uint64_t>( "clear_interval", 10000 );
        m_next   = m_clear;
    }
    void tick( uint64_t now ) override {
        if ( now < m_next ) return;
        ArbState& a = arbState();
        std::fill( a.rank.begin(), a.rank.end(), 0 );
        m_next = now + m_clear;
    }
    void onPick( unsigned host, unsigned, unsigned ) override {
        if ( (int)host == m_last ) m_streak++;
        else { m_last = host; m_streak = 1; }
        if ( m_streak > m_thresh && arbState().rank[host] == 0 ) {
            arbState().rank[host] = 1;
            m_blacklistings++;
        }
    }
    void finish() override { printf( "BTP_BLISS blacklistings=%lu\n", (unsigned long)m_blacklistings ); }
    std::string describe() override {
        return "bliss threshold=" + std::to_string( m_thresh ) + " clear_interval=" + std::to_string( m_clear );
    }
  private:
    unsigned m_thresh;
    uint64_t m_clear, m_next;
    int      m_last = -1;
    unsigned m_streak = 0;
    uint64_t m_blacklistings = 0;
};

//------------------------------------------------------------------------------------------------
class Atlas : public HostSched {
  public:
    Atlas( Params& p ) {
        m_quantum = p.find<uint64_t>( "quantum", 10000000 );
        m_alpha   = p.find<double>( "alpha", 0.875 );
        // over-threshold rule: requests older than this many pool cycles go first (0 = off); paper value 100K
        arbState().overThresh = p.find<uint64_t>( "threshold", 100000 );
        m_next    = m_quantum;
        m_as.assign( arbState().numHosts, 0.0 );
        m_total.assign( arbState().numHosts, 0.0 );
    }
    void onPick( unsigned host, unsigned openRow, unsigned row ) override {
        m_as[host] += arbState().serviceCycles( openRow, row );
    }
    void tick( uint64_t now ) override {
        if ( now < m_next ) return;
        for ( unsigned h = 0; h < m_as.size(); h++ ) {
            m_total[h] = m_alpha * m_total[h] + ( 1.0 - m_alpha ) * m_as[h];
            m_as[h] = 0.0;
        }
        ranksByKey( m_total, true );   // least attained service first
        printf( "BTP_ATLAS t=%lu ranks=%s\n", (unsigned long)now, ranksString().c_str() );
        m_next = now + m_quantum;
    }
    std::string describe() override {
        char b[128]; snprintf( b, sizeof b, "atlas quantum=%lu alpha=%.3f threshold=%lu", (unsigned long)m_quantum, m_alpha,
                               (unsigned long)arbState().overThresh );
        return b;
    }
    void finish() override {
        ArbState& a = arbState();
        std::string ad, pk;
        for ( unsigned h = 0; h < a.numHosts; h++ ) {
            ad += ( h ? "," : "" ) + std::to_string( a.overAdmits[h] );
            pk += ( h ? "," : "" ) + std::to_string( a.overPicks[h] );
        }
        printf( "BTP_ATLAS_END over_threshold_admits=%s over_threshold_picks=%s\n", ad.c_str(), pk.c_str() );
    }
  private:
    uint64_t m_quantum, m_next;
    double   m_alpha;
    std::vector<double> m_as, m_total;
};

//------------------------------------------------------------------------------------------------
class Tcm : public HostSched {
  public:
    Tcm( Params& p ) {
        m_quantum = p.find<uint64_t>( "quantum", 1000000 );
        m_shuffle = p.find<uint64_t>( "shuffle_interval", 800 );
        m_thresh  = p.find<double>( "cluster_thresh", 4.0 / 24.0 );
        m_sample  = p.find<uint64_t>( "blp_sample", 64 );
        unsigned n = arbState().numHosts;
        m_use.assign( n, 0.0 ); m_blp.assign( n, 0.0 ); m_pops.assign( n, 0 ); m_hits.assign( n, 0 );
        m_nextQ = m_quantum;
        m_nextS = m_shuffle;
    }
    void onPick( unsigned host, unsigned openRow, unsigned row ) override {
        m_use[host] += arbState().serviceCycles( openRow, row );
        m_pops[host]++;
        if ( openRow == row ) m_hits[host]++;
    }
    void tick( uint64_t now ) override {
        ArbState& a = arbState();
        if ( m_sample && now % m_sample == 0 ) {   // bank-level parallelism: banks a host is waiting on
            for ( const std::vector<uint64_t>* w : a.bankWaiting )
                for ( unsigned h = 0; h < a.numHosts; h++ ) if ( (*w)[h] ) m_blp[h] += 1.0;
            m_samples++;
        }
        if ( now >= m_nextQ ) { recluster( now ); m_nextQ = now + m_quantum; }
        if ( now >= m_nextS && m_bw.size() > 1 ) {
            m_offset = ( m_offset + 1 ) % m_bw.size();
            assign();
            m_nextS = now + m_shuffle;
        }
    }
    std::string describe() override {
        char b[128]; snprintf( b, sizeof b, "tcm quantum=%lu shuffle_interval=%lu cluster_thresh=%.4f",
                               (unsigned long)m_quantum, (unsigned long)m_shuffle, m_thresh );
        return b;
    }
  private:
    void recluster( uint64_t now ) {
        ArbState& a = arbState();
        unsigned n = a.numHosts;
        std::vector<unsigned> byUse( n );
        std::iota( byUse.begin(), byUse.end(), 0 );
        std::stable_sort( byUse.begin(), byUse.end(), [&]( unsigned x, unsigned y ) { return m_use[x] < m_use[y]; } );
        double total = std::accumulate( m_use.begin(), m_use.end(), 0.0 ), sum = 0.0;
        m_lat.clear(); m_bw.clear();
        for ( unsigned h : byUse ) {
            if ( sum + m_use[h] <= m_thresh * total ) { m_lat.push_back( h ); sum += m_use[h]; }
            else m_bw.push_back( h );
        }
        // niceness = rank by bank-level parallelism (higher = nicer) - rank by row-hit rate (higher = less nice)
        std::vector<double> blp( n ), rbl( n );
        for ( unsigned h = 0; h < n; h++ ) {
            blp[h] = m_samples ? m_blp[h] / m_samples : 0.0;
            rbl[h] = m_pops[h] ? (double)m_hits[h] / m_pops[h] : 0.0;
        }
        std::vector<double> nice( n, 0.0 );
        for ( unsigned x : m_bw ) {
            int b = 0, r = 0;
            for ( unsigned y : m_bw ) { if ( blp[y] < blp[x] ) b++; if ( rbl[y] < rbl[x] ) r++; }
            nice[x] = b - r;
        }
        std::stable_sort( m_bw.begin(), m_bw.end(), [&]( unsigned x, unsigned y ) { return nice[x] > nice[y]; } );
        m_offset = 0;
        assign();
        std::string lat, bw;
        for ( unsigned h : m_lat ) lat += std::to_string( h ) + " ";
        for ( unsigned h : m_bw )  bw  += std::to_string( h ) + " ";
        printf( "BTP_TCM t=%lu latency_cluster=[ %s] bandwidth_cluster=[ %s] ranks=%s\n",
                (unsigned long)now, lat.c_str(), bw.c_str(), ranksString().c_str() );
        std::fill( m_use.begin(), m_use.end(), 0.0 ); std::fill( m_blp.begin(), m_blp.end(), 0.0 );
        std::fill( m_pops.begin(), m_pops.end(), 0 ); std::fill( m_hits.begin(), m_hits.end(), 0 );
        m_samples = 0;
    }
    void assign() {
        ArbState& a = arbState();
        for ( unsigned i = 0; i < m_lat.size(); i++ ) a.rank[ m_lat[i] ] = i;
        for ( unsigned i = 0; i < m_bw.size(); i++ )
            a.rank[ m_bw[ ( i + m_offset ) % m_bw.size() ] ] = m_lat.size() + i;
    }
    uint64_t m_quantum, m_shuffle, m_sample, m_nextQ, m_nextS, m_samples = 0;
    double   m_thresh;
    unsigned m_offset = 0;
    std::vector<double>   m_use, m_blp;
    std::vector<uint64_t> m_pops, m_hits;
    std::vector<unsigned> m_lat, m_bw;
};

//------------------------------------------------------------------------------------------------
class ParBs : public HostSched {
  public:
    ParBs( Params& p ) {
        m_cap = p.find<unsigned>( "cap", 5 );
        arbState().bankOrder = BankOrder::MARK_ROWHIT_RANK_AGE;
    }
    void tick( uint64_t now ) override {
        ArbState& a = arbState();
        if ( ! a.marked.empty() ) return;
        // form a new batch
        unsigned n = a.numHosts;
        std::vector<double> maxLoad( n, 0.0 ), total( n, 0.0 );
        std::vector<unsigned> cnt( n );
        bool any = false;
        for ( std::list<Transaction*>* q : a.queues ) {
            std::fill( cnt.begin(), cnt.end(), 0 );
            for ( Transaction* t : *q ) {
                unsigned h = a.hostOf( t->addr );
                if ( cnt[h] < m_cap ) { cnt[h]++; a.marked.insert( t ); any = true; }
            }
            for ( unsigned h = 0; h < n; h++ ) {
                maxLoad[h] = std::max( maxLoad[h], (double)cnt[h] );
                total[h] += cnt[h];
            }
        }
        if ( ! any ) return;
        // rank: fewest marked requests in the busiest bank first, then fewest in total
        std::vector<double> key( n );
        for ( unsigned h = 0; h < n; h++ ) key[h] = maxLoad[h] * 1e6 + total[h];
        ranksByKey( key, true );
        m_batches++;
    }
    void finish() override { printf( "BTP_PARBS batches=%lu\n", (unsigned long)m_batches ); }
    std::string describe() override { return "parbs cap=" + std::to_string( m_cap ); }
  private:
    unsigned m_cap;
    uint64_t m_batches = 0;
};

//------------------------------------------------------------------------------------------------
class Saa : public HostSched {
  public:
    Saa( Params& p ) {
        ArbState& a = arbState();
        m_epoch     = p.find<uint64_t>( "epoch", 12000 );
        m_reserve   = p.find<unsigned>( "reserve", 4 );
        m_light     = p.find<double>( "light_share", 0.1 );
        m_imbalance = p.find<double>( "imbalance", 1.1 );
        m_link      = p.find<double>( "link_cycles", 300.0 );       // 250 ns at 1.2 GHz
        m_base      = p.find<double>( "base_cycles", 324.0 );       // 270 ns: empty-pool round trip
        m_peak      = p.find<double>( "peak_per_cycle", 0.219 ) * a.numChannels;   // requests per cycle
        m_estimate  = p.find<std::string>( "estimate", "bandwidth" ); // bandwidth | latency
        m_smooth    = p.find<double>( "smooth", 0.0 );   // weight of the previous epoch's estimate (0 = no smoothing)
        m_log       = p.find<unsigned>( "log_every", 10 );          // epochs between log lines (0 = off)
        if ( a.bankLevel ) a.runCap = p.find<unsigned>( "run_cap", 0 );   // 0 = off
        unsigned n = a.numHosts;
        m_lastServed.assign( n, 0 ); m_lastLat.assign( n, 0 ); m_lastSlot.assign( n, 0.0 ); m_lastBank.assign( n, 0 );
        m_sLat.assign( n, 1.0 ); m_sBw.assign( n, 1.0 ); m_sm.assign( n, 1.0 ); m_isLight.assign( n, false ); m_active.assign( n, false );
        m_next = m_epoch;
    }
    void tick( uint64_t now ) override {
        if ( now < m_next ) return;
        m_next = now + m_epoch;
        ArbState& a = arbState();
        unsigned n = a.numHosts;
        std::vector<double> dS( n );
        double sumS = 0;
        for ( unsigned h = 0; h < n; h++ ) { dS[h] = a.served[h] - m_lastServed[h]; sumS += dS[h]; }
        for ( unsigned h = 0; h < n; h++ ) {
            m_active[h] = dS[h] > 0;
            m_isLight[h] = sumS > 0 && dS[h] / sumS < m_light;
            if ( dS[h] > 0 ) {
                double L = ( a.devLatency[h] - m_lastLat[h] ) / dS[h] + m_link;
                double I = ( ( a.slotInterf[h] - m_lastSlot[h] ) + ( a.bankInterf[h] - m_lastBank[h] ) ) / dS[h];
                // the alone latency can't be below the empty-pool round trip (base_cycles), so the
                // estimate is capped at L / base_cycles when the measured interference nears L
                m_sLat[h] = L / std::max( L - I, m_base );
                double rate = dS[h] / m_epoch;
                double alone = std::min( rate * L / m_base, m_peak );
                m_sBw[h] = std::max( alone / rate, 1.0 );
            }
            m_lastServed[h] = a.served[h]; m_lastLat[h] = a.devLatency[h];
            m_lastSlot[h] = a.slotInterf[h]; m_lastBank[h] = a.bankInterf[h];
        }
        const std::vector<double>& raw = ( m_estimate == "bandwidth" ) ? m_sBw : m_sLat;
        for ( unsigned h = 0; h < n; h++ )
            if ( m_active[h] ) m_sm[h] = m_smooth * m_sm[h] + ( 1.0 - m_smooth ) * raw[h];
        const std::vector<double>& s = m_sm;
        double hi = 0, lo = 1e30;
        for ( unsigned h = 0; h < n; h++ ) if ( m_active[h] ) { hi = std::max( hi, s[h] ); lo = std::min( lo, s[h] ); }
        if ( hi > 0 && hi > m_imbalance * lo ) { ranksByKey( s, false ); m_rankedEpochs++; }   // most slowed first
        else std::fill( a.rank.begin(), a.rank.end(), 0 );
        m_epochs++;
        if ( m_log && m_epochs % m_log == 0 ) {
            std::string line;
            char b[96];
            for ( unsigned h = 0; h < n; h++ ) {
                snprintf( b, sizeof b, " h%u:lat=%.2f,bw=%.2f,used=%.2f,share=%.3f%s", h, m_sLat[h], m_sBw[h], m_sm[h],
                          sumS > 0 ? dS[h] / sumS : 0.0, m_isLight[h] ? ",light" : "" );
                line += b;
            }
            printf( "BTP_SAA t=%lu ranks=%s%s\n", (unsigned long)now, ranksString().c_str(), line.c_str() );
        }
    }
    int admitKey( unsigned host, unsigned chan, const std::vector<unsigned>& pend ) override {
        if ( m_isLight[host] && pend[host] < m_reserve ) return -1000;   // light-host guard
        return arbState().rank[host];
    }
    bool mayAdmit( unsigned host, unsigned chan, const std::vector<unsigned>& pend, unsigned pendTotal,
                   unsigned slots, const std::vector<bool>& waiting ) override {
        if ( pend[host] < m_reserve ) return true;           // within its own reservation
        unsigned held = 0;                                    // slots kept free for other active hosts
        for ( unsigned h = 0; h < pend.size(); h++ ) {
            if ( h == host || !( m_active[h] || waiting[h] ) ) continue;
            if ( pend[h] < m_reserve ) held += m_reserve - pend[h];
        }
        return pendTotal + held < slots;
    }
    void finish() override {
        printf( "BTP_SAA_END epochs=%lu ranked_epochs=%lu\n", (unsigned long)m_epochs, (unsigned long)m_rankedEpochs );
    }
    std::string describe() override {
        char b[200];
        snprintf( b, sizeof b, "saa epoch=%lu reserve=%u light_share=%.3f imbalance=%.3f run_cap=%u estimate=%s smooth=%.3f",
                  (unsigned long)m_epoch, m_reserve, m_light, m_imbalance, arbState().runCap, m_estimate.c_str(), m_smooth );
        return b;
    }
  private:
    uint64_t m_epoch, m_next, m_epochs = 0, m_rankedEpochs = 0;
    unsigned m_reserve, m_log;
    double   m_light, m_imbalance, m_link, m_base, m_peak, m_smooth;
    std::string m_estimate;
    std::vector<uint64_t> m_lastServed, m_lastLat, m_lastBank;
    std::vector<double>   m_lastSlot, m_sLat, m_sBw, m_sm;
    std::vector<bool>     m_isLight, m_active;
};

//------------------------------------------------------------------------------------------------
HostSched* makeHostSched( const std::string& name, Params& p ) {
    if ( name == "bliss" ) return new Bliss( p );
    if ( name == "atlas" ) return new Atlas( p );
    if ( name == "tcm" )   return new Tcm( p );
    if ( name == "parbs" ) return new ParBs( p );
    if ( name == "saa" )   return new Saa( p );
    return nullptr;
}

}
}
