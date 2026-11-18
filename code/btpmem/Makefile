# BTP SST element library: btpmem.timingDRAM (timingDRAM copy with lazyPop and the per-host front end), btpmem.frfcfsTransactionQ, btpmem.rowAddrMapper
SST_PREFIX ?= $(HOME)/sst-core
ELEM_SRC   ?= $(HOME)/sst-elements-library-14.0.0/src
CXX        := $(shell $(SST_PREFIX)/bin/sst-config --CXX)
CXXFLAGS   := $(shell $(SST_PREFIX)/bin/sst-config --ELEMENT_CXXFLAGS) -O2 \
              -I$(SST_PREFIX)/include/sst/core -I$(SST_PREFIX)/include/sst/elements/memHierarchy \
              -I$(ELEM_SRC) -I$(ELEM_SRC)/sst/elements/memHierarchy \
              -I$(ELEM_SRC)/sst/elements/memHierarchy/membackend
LDFLAGS    := $(shell $(SST_PREFIX)/bin/sst-config --ELEMENT_LDFLAGS) -L$(SST_PREFIX)/lib/sst-elements-library -l:libmemHierarchy.so -Wl,-rpath,$(SST_PREFIX)/lib/sst-elements-library

libbtpmem.so: btpTimingDRAM.cc btpTimingDRAM.h btpArb.h btpSched.cc frfcfsTransactionQ.cc rowAddrMapper.cc
	$(CXX) $(CXXFLAGS) -o $@ btpTimingDRAM.cc btpSched.cc frfcfsTransactionQ.cc rowAddrMapper.cc $(LDFLAGS)

clean:
	rm -f libbtpmem.so
