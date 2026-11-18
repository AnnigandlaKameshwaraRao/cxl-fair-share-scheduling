# Workloads

The experiments use 12 standard benchmarks: 6 aggressors that push the pool hard and 6 victims that need it for latency-critical or light access. Four of the 12 are AI workloads. Every workload was run alone for the same 400 ms simulated window and has checkpoints for all 4 hosts, so any workload can sit on any host in the mixes. The set was chosen from a broader list of 25 candidates; the section "Considered and removed" says why each of the others left.

## The simulated setup

All numbers in this document come from CXL-ClusterSim (gem5 hosts joined to an SST memory pool) on this configuration.

| Part | Setting | Why |
| --- | --- | --- |
| Hosts | 4, each with 4 cores at 3 GHz | 4 hosts give 3 aggressors + 1 victim mixes; 4 cores let one host keep enough misses in flight to load the pool |
| Core model in the measured region | gem5 TimingSimpleCPU (in-order, waits on each miss) | The fast detailed model that the simulator supports for multi-host runs; see Limits |
| Caches per host | 32 KiB L1d and 512 KiB L2 per core, 8 MiB shared L3 | Typical server-class sizes; every workload's data is far larger than the L3 |
| Cache miss limits (MSHRs) | L1d 16, L2 48, L3 192; write buffers 32 (L2) and 64 (L3) | Raised to server-like values so a host can have more misses outstanding, which raised 4-thread STREAM from 3.7–5.5 to 6.5–7.1 GB/s |
| Pool | 1 memory channel, 19.2 GB/s peak, about 240 ns unloaded round trip | One channel makes contention visible with 4 hosts |
| Memory per host | 1 GiB private slot in the pool; each workload bound to it with numactl --membind=1 | No data is shared between hosts, so any slowdown is contention |
| Measurement window | 400 ms of simulated time, statistics every 10 ms | Long enough to cover each workload's repeating phases; the same window for alone and shared runs |
| Checkpoints | Boot and setup under KVM, then a checkpoint just before the measured work, one per host slot (4 per workload) | Every run starts from the same state; slot i matches host i's pool address range |

## The 12 workloads

Aggressors each take 2.6–7.2 GB/s of the pool when alone, with 15–42 requests in flight. Victims take 1.4 GB/s or less, with 1–6.5 in flight, so their speed is set by pool latency rather than by bandwidth.

| Workload | Role | Suite | Domain | Alone pool bandwidth (GB/s) | Share of 19.2 GB/s | Range per 10 ms (GB/s) | Mean latency (ns) | Requests in flight | Checkpoint taken at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tealeaf | Aggressor | SPEC CPU 2026 (811.tealeaf\_s) | Heat conduction, implicit solver | 7.17 | 37% | 6.19–8.28 | 461 | 38.6 | 20 s into the run |
| STREAM | Aggressor | McCalpin STREAM | Memory bandwidth | 6.59 | 34% | 0.06–8.06 | 534 | 41.8 | Its ROI marker |
| fotonik3d | Aggressor | SPEC CPU 2026 (849.fotonik3d\_s) | Electromagnetics, FDTD | 5.58 | 29% | 1.96–11.06 | 353 | 24.8 | 12 s into the run |
| streamcluster | Aggressor | PARSEC | Online clustering | 4.17 | 22% | 0.19–4.89 | 294 | 23.4 | Its ROI marker |
| roms | Aggressor | SPEC CPU 2026 (865.roms\_s) | Ocean model | 3.63 | 19% | 0.36–7.64 | 329 | 24.2 | 15 s into the run |
| LLM inference | Aggressor, AI | llama.cpp (llama-bench) | Language-model decode | 2.61 | 14% | 0.00–3.16 | 283 | 14.9 | Its ROI marker |
| merci4 | Victim, AI | MERCI | Recommendation (embedding reduction) | 1.40 | 7% | 0.77–5.99 | 279 | 5.4 | Its ROI marker |
| graph500 BFS | Victim | SPEC CPU 2026 (854.graph500\_s) | Graph traversal | 1.00 | 5% | 0.98–1.00 | 256 | 5.3 | 4 s into the run |
| hnswlib | Victim, AI | hnswlib with BIGANN (SIFT) vectors | Vector search for RAG retrieval | 0.41 | 2% | 0.15–0.77 | 268 | 6.5 | Its ROI marker |
| cactus | Victim | SPEC CPU 2026 (809.cactus\_s) | Numerical relativity | 0.29 | 1.5% | 0.27–0.37 | 271 | 1.9 | 5 s into the run |
| multichase | Victim | Google multichase | Memory latency | 0.23 | 1.2% | 0.23–0.24 | 245 | 1.0 | Its ROI marker |
| Marian | Victim, AI | SPEC CPU 2026 (772.marian\_r) | Neural machine translation | under 0.05 | 0% | 0.00–0.04 | 279 | 5.6 | 15 s into the run |

All rows are alone runs on host slot 0 with the 1-channel pool. Bandwidth, latency and requests in flight are averages over the whole 400 ms window, weighted by time; latency is the mean pool round trip. The SPEC benchmarks have no ROI markers in their standard source, so their checkpoint is taken a fixed time after the program starts, chosen from a timing probe so it lands in the main phase. Marian's in-flight figure does not match its near-zero bandwidth; it most likely counts a few long-outstanding requests and should not be read as load.

## Alone bandwidth at a glance

The means separate the two roles cleanly. The ranges show which aggressors burst (fotonik3d, roms, STREAM between kernels) and which hold steady (tealeaf). merci4's high end is its cache flush before the measured region.

## Why each workload is in

The set covers six domains on each side, and each AI workload stands for a real reason operators pool memory.

### Aggressors

- **tealeaf** (SPEC CPU 2026). A heat-conduction mini-app with an implicit solver on a 5-point stencil, from the University of Bristol. It is the strongest and steadiest aggressor: 6.2–8.3 GB/s in every 10 ms window, alternating two phases about every 100 ms. Train input, 4 OpenMP threads.
- **STREAM**. McCalpin's sustainable-bandwidth benchmark, the standard memory hog in interference studies. It is the controlled upper bound. Arrays are 3× the usual size (25,165,824 doubles each) so its Copy, Scale, Add and Triad kernels fill the 400 ms window. 4 threads.
- **fotonik3d** (SPEC CPU 2026). Finite-difference time-domain simulation of a photonic waveguide. Mean 5.6 GB/s, with phases up to 11.1 GB/s, the highest peak of any workload. Its bursts test how the scheduler handles sudden load. Train input, 4 threads.
- **streamcluster** (PARSEC). Online k-median clustering of a stream of points, a data-mining kernel. Steady 4.5 GB/s after its first 60 ms, 96% reads. Native input, 4 threads.
- **roms** (SPEC CPU 2026). The Regional Ocean Modeling System, a production ocean model. Mean 3.6 GB/s, swinging between 0.4 and 7.6 GB/s about every 60 ms. It adds a periodic aggressor to the set. Train input, 4 threads.
- **LLM inference** (llama.cpp, AI). Text generation reads every model weight once per token, so decode streams memory while doing real work. It is the realistic AI noisy neighbour: 2.8 GB/s per repetition, with short gaps between repetitions. Model SmolLM2-135M in Q8\_0 (138 MiB), llama-bench with 5 repetitions, 4 threads.

### Victims

- **merci4** (MERCI, AI). The embedding-reduction step of DLRM-style recommendation, on the published DBLP dataset with 4 threads. Its random row gathers keep only about 5 requests in flight on our cores, so it is a moderate, latency-bound victim at 0.96 GB/s in its measured region. MERCI's own 48 MB cache flush runs in the first 100 ms of the window, which is where the 5.99 GB/s peak comes from.
- **graph500 BFS** (SPEC CPU 2026). The Graph500 breadth-first search, the standard data-intensive graph benchmark. All 4 threads are busy, yet it holds a flat 1.0 GB/s with about one miss per core: every hop waits for the last. That makes it our strongest latency probe after multichase.
- **hnswlib** (AI). Approximate nearest-neighbour search on an HNSW graph over 1 million BIGANN (SIFT) vectors, the retrieval step of RAG. Each hop depends on the distances just computed, so it is latency-bound: 0.41 GB/s on 1 thread. It runs the upstream sweep of 46 search settings; each query batch is one measured region.
- **cactus** (SPEC CPU 2026). Numerical relativity with the Einstein Toolkit (finite differences, explicit time stepping). Very flat at 0.29 GB/s with about half of its core time spent waiting on the pool, so its slowdown tracks pool latency cleanly. It replaced bc to add a scientific-computing victim. Train input, 4 threads.
- **multichase** (Google). Pure pointer chasing: each load's address comes from the previous load, exactly 1 request in flight. It is the reference victim, already used in our earlier studies. 256 MiB buffer, 1 thread, 15 samples of 25 ms, so the chase runs to the end of the 400 ms window.
- **Marian** (SPEC CPU 2026, AI). Neural machine translation (English to German) with a distilled transformer, the engine behind Microsoft Translator. On our cores it decodes almost entirely from cache: about 18 million instructions per 10 ms on one core with under 0.05 GB/s of pool traffic. It is the light AI tenant that shows how little a cache-friendly workload suffers. The rate version (772.marian\_r) runs 1 thread by SPEC's design.

## How we narrowed it down

Of 25 candidates, 12 were kept. Every workload had to meet three rules: a standard benchmark we can build unmodified, data that fits the host's 1 GiB pool slot, and a clear role when simulated. cactus and graph500 BFS were tried as aggressors and moved to the victims instead of being dropped. Each removal is explained in the next section.

## Considered and removed

Most candidates left for one of three reasons: too weak on our in-order cores, too big for the 1 GiB pool slot, or a near-duplicate of a workload we kept.

| Candidate | Suite | Tried as | What we found | Decision |
| --- | --- | --- | --- | --- |
| RandomAccess (GUPS) | HPC Challenge rule, upstream GUPS program | Random-access aggressor | 1.66 GB/s alone, 3.4 requests in flight; with out-of-order cores 1.57 GB/s, no better | Dropped: weaker than every final aggressor; LLM took the 6th aggressor place |
| pr (PageRank) | GAPBS | Aggressor | Flat 1.49 GB/s, 10 in flight | Dropped: same tier as GUPS; graph analytics is covered by graph500 BFS |
| bc (betweenness centrality) | GAPBS | Victim | 1.1 GB/s, 10 in flight | Replaced by cactus: bc and graph500 BFS are both graph traversals with the same access pattern |
| bfs | GAPBS | Victim | Not run | Covered by graph500 BFS, the more widely recognised version |
| lbm | SPEC CPU 2026 (782.lbm\_r) | Aggressor, as MemChannel uses it | Flat 1.00 GB/s with 2 copies, 2.8 in flight | Dropped: single-threaded, so on in-order cores it cannot keep enough misses in flight |
| cactus as an aggressor | SPEC CPU 2026 (809.cactus\_s) | 6th aggressor | 0.29 GB/s (8 GB/s natively) | Moved to the victims, where its flat, latency-sensitive behaviour is useful |
| graph500 BFS as an aggressor | SPEC CPU 2026 (854.graph500\_s) | 6th aggressor | 1.0 GB/s (14–15 GB/s natively): each core waits on one dependent miss | Moved to the victims |
| cloverleaf | SPEC CPU 2026 (820.cloverleaf\_s) | Aggressor | 20 GB/s natively, but 1.4 GB peak memory on the train input | Dropped: does not fit the 1 GiB pool slot |
| palm | SPEC CPU 2026 (822.palm\_s) | Aggressor | 16 GB/s natively, 1.6 GB peak memory | Dropped: does not fit |
| neutron | SPEC CPU 2026 (881.neutron\_s) | Aggressor | 21 GB/s natively for only about 6 s, 1.57 GB peak memory | Dropped: does not fit |
| Marian, speed version | SPEC CPU 2026 (872.marian\_s) | AI victim, 4 threads | 2.37 GB peak memory | Replaced by the rate version 772.marian\_r (1 thread, 844 MB) |
| sph\_exa | SPEC CPU 2026 (803.sph\_exa\_s) | Aggressor | 2–3 GB/s natively | Dropped: too weak before any simulation |
| pot3d | SPEC CPU 2026 (800.pot3d\_s) | Aggressor | Does not compile with our Fortran compiler (Fortran 2018 loop syntax errors) | Dropped rather than patched |
| memcached with memtier | memcached | Latency-critical service victim | Pool traffic about 4 MB/s: its working set stays in cache; latency shows a 1 ms timer step | Dropped: it barely touches the pool |
| DLRM in PyTorch | Meta DLRM | AI recommendation tenant | Needs vector instructions beyond the simulated CPU's SSE3/SSSE3 and a Python stack | Replaced by the MERCI C++ baseline, the setup Sun et al. used |
| AI training (DLRM, small networks) | Various | AI aggressor | Small models fit in the L3; large ones take days per step | Left out; each part of a training step has a stand-in (a short training step fits in the L3, and a large one takes days per step) |
| Spatter, NPB CG/MG/IS | Spatter, NAS | Extra patterns | Not needed | Gather patterns are covered by MERCI and hnswlib; HPC kernels by the SPEC workloads |
| Our own pointer-chase, GUPS and gather drivers | None (written by us) | Early microbenchmarks | Not standard benchmarks | Removed; replaced by multichase, upstream GUPS and MERCI |

Native figures are DRAM bandwidth measured on a desktop (Intel i7-12700, 4 threads, train input). Our in-order simulated cores reach about a third of that: tealeaf runs at 20 GB/s natively and 7.2 GB/s in simulation.

## Design decisions we weighed

The core model sets most of these: an in-order core keeps one demand miss in flight, so pool load comes from cores, prefetchers and miss limits, not from the program alone.

| Question | Options weighed | Chosen | Why |
| --- | --- | --- | --- |
| Cores per host | 1, 2 or 4 | 4 | Each in-order core has one demand miss outstanding, so more cores means more load on the pool. With 4, STREAM and tealeaf reach 6.6–7.2 GB/s |
| Cache miss limits | gem5 defaults or server-like values | Server-like (L1d 16, L2 48, L3 192 MSHRs) | Prefetchers and write-backs can then keep 24–42 requests in flight for the aggressors |
| Core model | In-order timing core or out-of-order core | In-order timing core | An out-of-order pilot on GUPS gave 1.57 GB/s against 1.66, ran 3× the instructions spinning at barriers, and needed over 8 GB of memory per host |
| Input sizes | SPEC ref, train or test inputs | Train, where the peak memory fits 1 GiB | Ref inputs exceed the pool slot; train inputs still reach the main phase within seconds |
| Measurement window | Each workload's own region, or one fixed window | 400 ms for every workload, statistics every 10 ms | In a mix all hosts run on one clock, so a common window compares the same span of time. Workloads are lengthened through their own options to fill it: STREAM arrays 3×, llama-bench 5 repetitions, multichase 15 samples |
| Where the checkpoint sits | ROI markers or a fixed delay | Markers where the source has them; a fixed delay for SPEC | SPEC source has no markers and we keep it unmodified. Each delay was checked with a timing probe (process memory and CPU time every 0.5 s) so the checkpoint lands in the main phase |
| AI coverage | None, or several AI tenants | 4 of 12 (LLM, MERCI, hnswlib, Marian) | MemChannel, the only multi-host CXL fairness study, has no AI workloads; AI is the main reason pools are built |
| How many slots per workload | Only the hosts first planned, or every host | All 4 slots for all 12 workloads | Any workload can run on any host, so a mix can put any workload in any slot |
| Where the runs execute | Desktop, cluster, or desktop CPU with cluster memory over the LAN | Cluster for the mix matrix, desktop for pilots and alone runs | A 4-host mix needs about 14–16 GB; memory over a 1 Gb/s LAN was considered and rejected |

Graph500's checkpoint shows why the probes matter. At 2 s it caught the input file still loading (0.45 GB/s); the probe showed BFS runs from about 2.7 to 6.3 s, so the checkpoint moved to 4 s.

## Changes beyond upstream source

Every workload is the published benchmark. Only hnswlib and multichase change source beyond ROI markers (hnswlib two size constants, multichase a build-time switch for its sampling period); everything else below is a marker, a build flag or the benchmark's own options.

| Workload | Change | Kind | Why |
| --- | --- | --- | --- |
| STREAM, streamcluster, llama-bench, MERCI, hnswlib, multichase | gem5 ROI markers around the measured work | Markers only, as gem5-resources does | Lets the checkpoint and the statistics line up with the measured region |
| streamcluster | Marker placed after the input points are generated | Marker position | PARSEC generates its input inside its own ROI; we measure clustering, not generation |
| hnswlib | Two size constants set for 1 million vectors | Source change, disclosed | The upstream benchmark targets 1 billion vectors; 1 million (a 277 MB index) fits the 1 GiB slot |
| multichase | gem5 ROI markers; sampling period made settable at build time (upstream fixes it at 0.5 s) and set to 25 ms; -n 15 samples | Markers; a 2-line build-time switch; command-line option | 15 samples of 25 ms cover the 400 ms window |
| STREAM | 25,165,824 elements per array | Size given to the program | Its kernels then last longer than the window |
| llama-bench | -r 5 repetitions; built for plain x86-64 | Command-line option; build target | Fills the window; the simulated CPU has no AVX |
| SPEC CPU 2026 floating-point builds | Linker flag forcing in the pthread functions libgfortran needs (-Wl,-u,pthread\_...) | Link flag, no source change | In a static build these weak references stay empty, and the Fortran benchmarks crashed when closing a file. With the flag all of them pass SPEC's own output check |
| graph500 | Runs only the BFS command of the train input | Input selection | The train input runs BFS and then an all-pairs shortest-path job on a road graph; running only BFS keeps one kernel in the window |
| Marian | Rate version 772.marian\_r, 1 thread | Benchmark choice | The 4-thread speed version needs 2.37 GB; the rate version is single-threaded by SPEC's design |

lbm also had an approved change (its grid set to the SPEC CPU 2017 size so it fits), but lbm is not in the final set.

## Limits of this setup

The main limit is the in-order core: it underestimates how hard each host can push the pool, so the results speak to relative harm between hosts more than to absolute bandwidth.

- **Lower demand per host.** Natively, tealeaf, fotonik3d and graph500 BFS reach 14–20 GB/s; here they reach 1.0–7.2 GB/s. Workloads that rely on many independent misses (graph500, GUPS, MERCI) lose the most, which is why they ended up as victims.
- **Phases.** roms, fotonik3d, STREAM and the LLM change behaviour within the window. In a mix, which phases overlap depends on each host's checkpoint, so results are read per 10 ms window as well as over the whole 400 ms.
- **Light victims.** Marian (under 0.05 GB/s) and cactus (0.29 GB/s) touch the pool little, so their slowdowns are small by design. They show how far harm reaches, not its peak.
- **Train inputs.** The 1 GiB slot rules out SPEC's reference inputs. The train inputs run the same code paths at a smaller size.
- **One baseline slot.** Alone runs used host slot 0. The other slots differ only in their pool address range, so we expect the same alone behaviour.

## Sources

1. SPEC CPU 2026 benchmark descriptions: [811.tealeaf\_s](https://www.spec.org/cpu2026/Docs/benchmarks/811.tealeaf_s.html), [849.fotonik3d\_s](https://www.spec.org/cpu2026/Docs/benchmarks/849.fotonik3d_s.html), [865.roms\_s](https://www.spec.org/cpu2026/Docs/benchmarks/865.roms_s.html), [854.graph500\_s](https://www.spec.org/cpu2026/Docs/benchmarks/854.graph500_s.html), [809.cactus\_s](https://www.spec.org/cpu2026/Docs/benchmarks/809.cactus_s.html), [772.marian\_r](https://www.spec.org/cpu2026/Docs/benchmarks/772.marian_r.html)
2. [STREAM](https://www.cs.virginia.edu/stream/ref.html), J. McCalpin
3. [PARSEC benchmark suite](https://parsec.cs.princeton.edu/), Princeton University (streamcluster)
4. [llama.cpp](https://github.com/ggml-org/llama.cpp) and its [llama-bench tool](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md)
5. [MERCI](https://github.com/SNU-ARC/MERCI), embedding-reduction baseline
6. [hnswlib](https://github.com/nmslib/hnswlib) and [ann-benchmarks](https://github.com/erikbern/ann-benchmarks)
7. [Graph500](https://graph500.org/)
8. [Google multichase](https://github.com/google/multichase)
9. [HPC Challenge](https://hpcchallenge.org/hpcc/) (RandomAccess) and [GAP Benchmark Suite](https://github.com/sbeamer/gapbs) (bc, pr, bfs)
10. [MemChannel](https://arxiv.org/abs/2608.21731), NSDI 2026; [Demystifying CXL Memory](https://arxiv.org/abs/2303.15375), Sun et al., MICRO 2023

All measured numbers are from our CXL-ClusterSim runs: 400 ms alone windows on host slot 0, 1-channel pool.
