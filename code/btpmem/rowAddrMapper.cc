// BTP: memHierarchy.simpleAddrMapper with a settable row size, registered as btpmem.rowAddrMapper.
//
// simpleAddrMapper puts 256 consecutive 64 B lines of a channel in one bank row (a fixed
// 8-bit column field), so every row is 16 KiB whatever "row_size" says. This copy keeps
// the same bit layout (line offset | channel | column | rank | bank | row) and only sizes
// the column field from "row_size": 8KiB gives a DDR4 rank's page, 4KiB a DDR5 x8/x16
// subchannel's. row_size = 16KiB reproduces simpleAddrMapper exactly.
//
// Derived from SST-Elements 14.0.0 memHierarchy simpleAddrMapper. Copyright 2009-2024 NTESS,
// BSD 3-Clause licence (see THIRD_PARTY.md).

#include <sst/core/sst_config.h>
#include "sst/elements/memHierarchy/memTypes.h"   // Addr
#include <sst/core/unitAlgebra.h>
#include <sst/core/output.h>
#include "timingAddrMapper.h"

namespace SST {
namespace BTP {

using SST::MemHierarchy::TimingDRAM_NS::AddrMapper;
using namespace SST::MemHierarchy;   // isPowerOfTwo, log2Of

class RowAddrMapper : public AddrMapper {
  public:
    SST_ELI_REGISTER_MODULE(RowAddrMapper, "btpmem", "rowAddrMapper", SST_ELI_ELEMENT_VERSION(1,0,0),
            "simpleAddrMapper layout with a settable row size", SST::MemHierarchy::TimingDRAM_NS::AddrMapper)

    SST_ELI_DOCUMENT_PARAMS(
        {"row_size", "(string) Bytes of consecutive address kept in one bank row; power of 2, at least 64B", "16KiB"} )

    RowAddrMapper( Params &params ) : AddrMapper(), m_baseShift( 6 ) {
        Output output("", 1, 0, Output::STDOUT);
        UnitAlgebra rowSize = UnitAlgebra(params.find<std::string>("row_size", "16KiB"));
        if ( !rowSize.hasUnits("B") )
            output.fatal(CALL_INFO, -1, "btpmem.rowAddrMapper: row_size must have units of B\n");
        uint64_t lines = rowSize.getRoundedValue() / 64;
        if ( lines == 0 || !isPowerOfTwo(lines) )
            output.fatal(CALL_INFO, -1, "btpmem.rowAddrMapper: row_size must be a power of 2, at least 64B\n");
        m_columnShift = log2Of( lines );
        output.verbose(CALL_INFO, 1, 0, "btpmem.rowAddrMapper: row_size %" PRIu64 " B (%" PRIu64 " lines)\n",
                       rowSize.getRoundedValue(), lines);
    }

    virtual void setNumChannels( unsigned int num ) { check(num, "channels"); m_numChannels = num; }
    virtual void setNumRanks( unsigned int num )    { check(num, "ranks");    m_numRanks = num; }
    virtual void setNumBanks( unsigned int num )    { check(num, "banks");    m_numBanks = num; }

    int getChannel( Addr addr ) { return ( addr >> channelShift() ) & ( m_numChannels - 1 ); }
    int getRank( Addr addr )    { return ( addr >> rankShift() ) & ( m_numRanks - 1 ); }
    int getBank( Addr addr )    { return ( addr >> bankShift() ) & ( m_numBanks - 1 ); }
    int getRow( Addr addr )     { return addr >> rowShift(); }

  private:
    void check( unsigned num, const char* what ) {
        if ( !isPowerOfTwo(num) ) {
            Output output("", 1, 0, Output::STDOUT);
            output.fatal(CALL_INFO, -1, "btpmem.rowAddrMapper: number of %s must be a power of 2\n", what);
        }
    }
    int channelShift() { return m_baseShift; }
    int rankShift()    { return m_columnShift + channelShift() + log2Of( m_numChannels ); }
    int bankShift()    { return rankShift() + log2Of( m_numRanks ); }
    int rowShift()     { return bankShift() + log2Of( m_numBanks ); }

    unsigned m_baseShift;
    unsigned m_columnShift;
};

}
}
