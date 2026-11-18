# Workloads

Every workload is a published benchmark built from its upstream source. The only changes are gem5 region-of-interest markers, plus the disclosed exceptions below. Doc 07 explains why each workload was chosen and what each one does on the simulated pool.

## Files

- `patches/roi.h`: the shared marker header. It calls the guest's `m5` tool, one command per call, the same way STREAM's gem5 version does. Built without `-DGEM5_ANNOTATION`, every marker does nothing.
- `patches/*.patch`: marker patches for llama-bench, MERCI, hnswlib, multichase and streamcluster, and for upstream GUPS (a candidate that was tested and dropped). Each patch includes `roi.h` by a relative path; put `roi.h` where the patch's `#include` expects it, or change the path.
- `joblists/wl_<tag>_4slot.json`: the run configuration of each workload for each of the four host slots: guest command, cores, caches, pool address range. The experiment joblists in `code/experiments/` are built from these.

## Build

The simulated CPU reports only SSE3/SSSE3, so every binary is built for plain `x86-64`. Each program is built twice: `<name>.native` (markers off, for checks on a real machine) and `<name>.m5` (markers on, for the simulator). The binaries, models and data go into the guest disk image under `/home/gem5/btp-workloads`.

| Workload | Upstream source and version | Build (the `.m5` build adds `-DGEM5_ANNOTATION`) | Input |
| --- | --- | --- | --- |
| STREAM | [simple-vectorizable-microbenchmarks](https://github.com/kaustav-goswami/simple-vectorizable-microbenchmarks) at `3cb3dcb38652`, `stream-syscalls` | its `makefiles/Makefile-hw` (the `stream.hw.m5` target) | 25,165,824 doubles per array, 4 threads |
| streamcluster | PARSEC 2.2, taken from the gem5-resources git history (commit `a926465d`'s parent, `src/parsec/.../pkgs/kernels/streamcluster`) + `streamcluster-roi.patch` | `g++ -O3 -march=x86-64 -DENABLE_THREADS -pthread streamcluster.cpp parsec_barrier.cpp` | native input: `10 20 128 1000000 200000 5000 none out.txt 4` |
| LLM inference | [llama.cpp](https://github.com/ggml-org/llama.cpp) tag `b11750` (`dd002b91f583`) + `llama-bench-roi.patch` | `cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_SSE42=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_BMI2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_AVX512=OFF -DGGML_OPENMP=ON -DCMAKE_C_FLAGS="-march=x86-64 -mtune=generic" -DCMAKE_CXX_FLAGS="-march=x86-64 -mtune=generic"`, target `llama-bench` | ggml-org SmolLM2-135M Q8_0 GGUF; `-p 0 -n 2 -t 4 -r 5` |
| MERCI | [MERCI](https://github.com/SNU-ARC/MERCI) at `cce40ac946e2` + `merci-roi.patch` | in `4_performance_evaluation`: `g++ -include array -o merci_baseline src/eval_baseline.cc -I. -O3 -W -std=c++17 -fopenmp -march=x86-64 -mtune=generic -ffast-math -lstdc++fs` | DBLP dataset prepared with MERCI's own scripts; `-d dblp -c 4 -r 2` |
| hnswlib | [hnswlib](https://github.com/nmslib/hnswlib) at `ca426729609b` (v0.10.0-rc.2) + `hnswlib-sift1b.patch` | `g++ -O2 -march=x86-64 -mtune=generic -fopenmp -I. -DBTP_QSIZE=20 tests/cpp/main.cpp tests/cpp/sift_1b.cpp` | first 1 M vectors of BIGANN (SIFT1B); 1 thread |
| multichase | [multichase](https://github.com/google/multichase) at `8b68e918f8d2` + `multichase-roi.patch` | `make multichase CFLAGS="<its CFLAGS> -DDELAY_USECS=25000"` | `-m 256m -n 15`, 1 thread |
| tealeaf, fotonik3d, roms, graph500, cactus, Marian | SPEC CPU 2026 (811.tealeaf_s, 849.fotonik3d_s, 865.roms_s, 854.graph500_s, 809.cactus_s, 772.marian_r) | SPEC's own build tools, statically linked for `x86-64`, 4 OpenMP threads; the Fortran benchmarks also need `-Wl,-u,<name>` link flags for the pthread functions libgfortran references (`pthread_cond_broadcast`, `_destroy`, `_signal`, `_wait`, `pthread_key_delete`, `pthread_mutex_destroy`, `_lock`, `_unlock`) | train inputs; graph500 runs only its BFS command; Marian runs 1 thread |

The exact guest commands are in `joblists/`. SPEC CPU 2026 is licensed: its sources, data, configuration and binaries are not in this repository, and anyone recreating the SPEC runs needs their own SPEC licence. The SPEC programs have no markers: the run script starts the program, waits a fixed time (4–20 s, chosen with a timing probe so setup is over) and then takes the checkpoint.

## Disclosed exceptions

- **hnswlib**: two size constants were changed (a 1 M-vector subset instead of 200 M, and the queries per search setting set at build time) so it fits the 1 GiB pool slot.
- **multichase**: its sampling period `DELAY_USECS` is a fixed constant upstream (0.5 s); the patch lets it be set at build time (2 lines), and the build sets 25 ms so 15 samples cover the window.
- **graph500**: runs only the BFS command of the train input.
- **Marian**: the rate version, which runs one thread by SPEC's design.
- **Longer runs to cover the window**: STREAM's array size, multichase's sample count (`-n 15`) and llama-bench's repeat count (`-r 5`) are set with their own options.
- **streamcluster**: its marker sits after the input points are generated, because PARSEC generates the input inside its own region of interest.

## Disk image

The guest image is the Ubuntu 24.04 x86 image built with [gem5-resources](https://github.com/kaustav-goswami/gem5-resources) (branch `disaggregated`), grown to 6 GiB with `virt-resize`. The workloads were copied in with `virt-customize --copy-in` to `/home/gem5/btp-workloads` (owner uid 1000); libevent libraries went to `/usr/local/lib` followed by `ldconfig`. The image also needs the gem5 guest tool `m5` at `/usr/local/bin/m5` (root-owned, setuid), the network fixes listed in doc 03, and STREAM's binaries under `/home/gem5/simple-vectorizable-microbenchmarks`.
