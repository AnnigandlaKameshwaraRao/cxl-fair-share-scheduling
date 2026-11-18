# Third-party software and licences

This repository holds only the project's own work and its changes to other projects. The software it builds on stays under its own licence and is not copied here, except where a file below is derived from it.

| Project | Used for | Licence | In this repository |
| --- | --- | --- | --- |
| [CXL-ClusterSim](https://github.com/darchr/cxl-clustersim) (gem5 fork) | Simulator of every host and the gem5–SST bridge | gem5's BSD 3-Clause licence | `code/simulator_patches/` are diffs against it and fall under its licence |
| [SST-Core and SST-Elements](https://github.com/sstsimulator) 14.0.0 | Simulator of the shared pool | BSD 3-Clause, Copyright NTESS | `code/btpmem/btpTimingDRAM.cc/.h` and `rowAddrMapper.cc` are modified copies of SST-Elements files and keep NTESS's notice |
| [gem5-resources](https://github.com/kaustav-goswami/gem5-resources) (branch `disaggregated`) | Linux kernel configuration and disk image build | BSD 3-Clause and the licences of its parts | Not included |
| Linux 6.9.9 | Guest kernel | GPL-2.0 | Not included |
| [simple-vectorizable-microbenchmarks](https://github.com/kaustav-goswami/simple-vectorizable-microbenchmarks) | STREAM, upstream GUPS | see its LICENSE | `code/workloads/patches/gups-upstream-roi.patch` (diff) |
| PARSEC 2.2 streamcluster | Workload | PARSEC licence | `streamcluster-roi.patch` (diff) |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Workload | MIT | `llama-bench-roi.patch` (diff) |
| [MERCI](https://github.com/SNU-ARC/MERCI) | Workload | see its LICENSE | `merci-roi.patch` (diff) |
| [hnswlib](https://github.com/nmslib/hnswlib) | Workload | Apache-2.0 | `hnswlib-sift1b.patch` (diff) |
| [multichase](https://github.com/google/multichase) | Workload | Apache-2.0 | `multichase-roi.patch` (diff) |
| SPEC CPU 2026 | Six workloads | SPEC licence agreement | Nothing: no source, data, configuration or binary |
| SmolLM2-135M (GGUF), BIGANN, DBLP | Model and data sets | their own terms | Not included |

The project's own code (`code/btpmem/btpSched.cc`, `btpArb.h`, `frfcfsTransactionQ.cc`, `code/run/`, `code/workloads/patches/roi.h`, `analysis/`) is under the BSD 3-Clause licence in `LICENSE`. The documentation and data are under CC BY 4.0 (`LICENSE-docs`).
