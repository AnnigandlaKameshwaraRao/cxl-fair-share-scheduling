# Phase 1: Each Workload Alone on the CXL Pool

Phase 1 ran each workload alone on one host attached to the simulated CXL pool, to measure how much of the pool it uses with no one else competing. **No single host saturates the pool.** The heaviest, tealeaf and STREAM, use 6.3–7.2 GB/s (33–37% of the channel's 19.2 GB/s peak) at 460–560 ns pool latency, against about 245 ns unloaded. The final set has 12 workloads, 6 aggressors and 6 victims. Each was run over a 400 ms window from all four pool slots, and these 48 runs are the baselines for Phase 1 – Mixed ([doc 09](09_phase1_mixed.md)).

## Setup

Each run has one simulated host (gem5) connected to a pool simulated in SST, the same CXL-ClusterSim setup as the main campaign.

| Part | Setting |
| --- | --- |
| Host CPU | 4 x86 cores at 3 GHz, gem5 timing CPU (in order, one memory access at a time per core) |
| Caches | per core: 32 KiB L1d and L1i (16 miss slots each), 512 KiB L2 (48 miss slots); shared 8 MiB L3 (192 miss slots); stride prefetchers |
| Guest | Ubuntu 24.04, workload data placed in the pool with `numactl --membind=1` |
| Host link | fixed 250 ns delay, no bandwidth limit |
| Pool | one DDR channel, 19.2 GB/s peak, 2 ranks x 16 banks, first-come-first-served queues |

Each workload boots and runs its setup under KVM, and a checkpoint is taken just before its measured region. The run restores that checkpoint into the detailed simulation. Statistics are reset when the region starts (the benchmark's `workbegin` marker) and dumped when it ends (`workend`). All pool figures below come from the host's side of the link: requests sent to the pool, their round-trip latency, and the number in flight. They cover the measured regions only.

## Final workload set: 400 ms window, all four slots

Each workload has four checkpoints, one per pool slot (the host position it takes in a mix), and each was run alone. A run restores the checkpoint, simulates a fixed 400 ms window and dumps statistics every 10 ms. Figures are averages over the whole window.

| Workload | Benchmark and input | Role |
| --- | --- | --- |
| tealeaf | SPEC CPU2026 811.tealeaf\_s, train input, 4 threads | aggressor |
| STREAM | simple-vectorizable-microbenchmarks, 25,165,824 elements per array, 4 threads | aggressor |
| fotonik3d | SPEC CPU2026 849.fotonik3d\_s, train input, 4 threads | aggressor |
| streamcluster | PARSEC 2.2, native input, 4 threads | aggressor |
| roms | SPEC CPU2026 865.roms\_s, train input, 4 threads | aggressor |
| LLM inference | llama.cpp `llama-bench`, SmolLM2-135M Q8\_0, 2-token decode, 5 repeats, 4 threads | aggressor |
| MERCI | MERCI baseline, DBLP data, 4 threads | victim |
| graph500 | SPEC CPU2026 854.graph500\_s, BFS step of the train input, 4 threads | victim |
| hnswlib | `sift_1b` example, 1M BIGANN vectors, 1 thread | victim |
| cactus | SPEC CPU2026 809.cactus\_s, train input, 4 threads | victim |
| multichase | multichase, 256 MB buffer, 15 samples, 1 thread | victim |
| Marian | SPEC CPU2026 772.marian\_r, train input, 1 thread | victim |

### Measurements per slot

Every column is measured the same way for every workload, over the whole 400 ms window; rates are per simulated second.

- **Pool latency** is the mean round trip of the host's pool requests, including the 250 ns link.
- **Latency above unloaded** compares it with 245 ns, what multichase sees with a single request in flight. It shows how much a workload queues behind its own requests when it is alone.
- **Instructions** counts instructions committed by all of the host's cores. MERCI's and multichase's counts also include instructions that are not the benchmark's work (spin and wait loops), so for those two the instruction rate does not track useful progress; their pool request rate does.
- **Instruction rate vs slot 0** shows how much the program phase at each checkpoint changes the speed.

| Workload | Slot | Pool GB/s | Pool latency (ns) | Latency above unloaded 245 ns | Instructions (billion per simulated s) | Instruction rate vs slot 0 | Pool requests (million per simulated s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tealeaf | 0 | 7.17 | 461 | +88% | 5.001 | — | 111.99 |
|  | 1 | 7.02 | 462 | +89% | 4.978 | 0% | 109.74 |
|  | 2 | 7.19 | 462 | +88% | 5.012 | 0% | 112.40 |
|  | 3 | 7.12 | 462 | +89% | 4.997 | 0% | 111.31 |
| STREAM | 0 | 6.59 | 534 | +118% | 0.929 | — | 103.04 |
|  | 1 | 6.32 | 559 | +128% | 0.908 | -2% | 98.70 |
|  | 2 | 6.28 | 560 | +128% | 0.908 | -2% | 98.09 |
|  | 3 | 6.49 | 542 | +121% | 0.927 | 0% | 101.42 |
| fotonik3d | 0 | 5.58 | 353 | +44% | 2.416 | — | 87.13 |
|  | 1 | 6.06 | 353 | +44% | 2.678 | +11% | 94.73 |
|  | 2 | 6.26 | 354 | +44% | 2.801 | +16% | 97.88 |
|  | 3 | 6.39 | 364 | +49% | 2.697 | +12% | 99.80 |
| streamcluster | 0 | 4.17 | 294 | +20% | 2.910 | — | 65.17 |
|  | 1 | 4.16 | 294 | +20% | 2.905 | 0% | 65.07 |
|  | 2 | 4.16 | 294 | +20% | 2.907 | 0% | 65.04 |
|  | 3 | 4.17 | 294 | +20% | 2.906 | 0% | 65.10 |
| roms | 0 | 3.63 | 329 | +34% | 4.013 | — | 56.76 |
|  | 1 | 3.93 | 319 | +30% | 4.229 | +5% | 61.45 |
|  | 2 | 4.07 | 316 | +29% | 4.228 | +5% | 63.65 |
|  | 3 | 3.77 | 313 | +28% | 4.180 | +4% | 58.98 |
| LLM inference | 0 | 2.61 | 283 | +15% | 6.539 | — | 40.76 |
|  | 1 | 2.65 | 283 | +15% | 6.537 | 0% | 41.34 |
|  | 2 | 2.66 | 283 | +15% | 6.555 | 0% | 41.49 |
|  | 3 | 2.68 | 283 | +15% | 6.594 | +1% | 41.82 |
| MERCI | 0 | 1.40 | 279 | +14% | 0.441 | — | 21.82 |
|  | 1 | 1.41 | 284 | +16% | 0.435 | -1% | 21.99 |
|  | 2 | 1.40 | 279 | +14% | 0.453 | +3% | 21.93 |
|  | 3 | 1.40 | 281 | +15% | 0.451 | +2% | 21.86 |
| graph500 | 0 | 1.00 | 256 | +4% | 0.506 | — | 15.62 |
|  | 1 | 1.00 | 256 | +4% | 0.502 | -1% | 15.62 |
|  | 2 | 1.00 | 256 | +4% | 0.507 | 0% | 15.59 |
|  | 3 | 1.45 | 277 | +13% | 0.764 | +51% | 22.65 |
| hnswlib | 0 | 0.41 | 268 | +10% | 1.316 | — | 6.37 |
|  | 1 | 0.41 | 268 | +9% | 1.328 | +1% | 6.34 |
|  | 2 | 0.40 | 269 | +10% | 1.307 | -1% | 6.27 |
|  | 3 | 0.41 | 269 | +10% | 1.314 | 0% | 6.34 |
| cactus | 0 | 0.29 | 271 | +10% | 1.422 | — | 4.53 |
|  | 1 | 1.53 | 364 | +49% | 1.078 | -24% | 23.93 |
|  | 2 | 1.26 | 372 | +52% | 1.103 | -22% | 19.71 |
|  | 3 | 0.25 | 271 | +11% | 1.561 | +10% | 3.90 |
| multichase | 0 | 0.23 | 245 | 0% | 0.017 | — | 3.66 |
|  | 1 | 0.23 | 245 | 0% | 0.016 | -3% | 3.66 |
|  | 2 | 0.23 | 245 | 0% | 0.022 | +28% | 3.66 |
|  | 3 | 0.23 | 245 | 0% | 0.019 | +15% | 3.66 |
| Marian | 0 | under 0.01 | 279 | +14% | 1.808 | — | 0.07 |
|  | 1 | under 0.01 | 243 | -1% | 1.799 | -1% | 0.04 |
|  | 2 | under 0.01 | 279 | +14% | 1.807 | 0% | 0.07 |
|  | 3 | under 0.01 | 278 | +14% | 1.809 | 0% | 0.07 |

- **The slot changes the result for three workloads.** cactus's slot 1 and 2 checkpoints fall in a phase that uses 4–6 times more pool bandwidth. graph500's slot 3 checkpoint runs 45% higher, and fotonik3d ranges from 5.6 to 6.4 GB/s. roms varies by 12% and STREAM by 5%; the rest stay within 2%. So each host in a mix is compared with the alone run from its own slot.
- **MERCI's 1.40 GB/s includes the end of its setup.** Its upstream cache flush runs until about 100 ms into the window; inside its query region it holds 0.96 GB/s.
- **The first streamcluster slot-2 checkpoint was faulty.** It sat idle from restore, alone and in its mix, so it was remade and both runs were repeated.
- **Where runs differ from the standard benchmark:** graph500 runs only the BFS step of its train input; Marian runs one thread, as the rate benchmark does; hnswlib has two size constants changed so it fits memory. STREAM's array size, multichase's sample count and llama-bench's repeats are set with their own command-line options so each covers the window. The SPEC programs have no code markers: their checkpoint is taken a fixed time into the run.

The rest of this doc covers the first workload set, measured over each benchmark's own marked regions rather than a fixed window. GUPS, bc and memcached were later replaced. STREAM, LLM inference, MERCI, hnswlib and multichase stayed, with longer runs so they cover the window.

## Workloads

All are unmodified upstream benchmarks with gem5 region markers added. The one exception is vector search, where two size constants in the hnswlib example were changed so it fits the simulated memory. Each region is one natural unit of the benchmark, so its length is set by the benchmark, not by us.

| Workload | Source | Options | Threads | One measured region | Regions | Simulated length of one region |
| --- | --- | --- | --- | --- | --- | --- |
| STREAM | simple-vectorizable-microbenchmarks | 8,388,608 elements | 4 | one kernel (copy, scale, add, triad) | 4 | 28–32 ms |
| LLM decode | llama.cpp `llama-bench`, SmolLM2-135M Q8\_0 | 2 tokens, 3 repeats | 4 | one 2-token decode | 3 | 106–109 ms |
| GUPS | simple-vectorizable-microbenchmarks | 4,194,304-entry table | 4 | the whole update run | 1 | 942 ms |
| MERCI (4 threads) | MERCI baseline, DBLP data | 2 repeats | 4 | one pass over the queries | 1 of 2 | 1.83 s |
| bc | GAP benchmark suite | Kronecker graph, scale 17, 3 trials | 4 | one trial | 3 | 48–50 ms |
| vector search | hnswlib `sift_1b` example, 1M BIGANN vectors | upstream search sweep | 1 | the queries at one search-effort setting | 46 | 4–90 ms (0.96 s in all) |
| multichase | multichase | 256 MB buffer | 1 | one timed pointer chase | 1 | 287 ms |
| memcached | memcached server, memtier client | 2 server threads, 2 client threads x 4 connections, random gets | 2 + 2 | one memtier get run | 3 | 1.01 s |

The second MERCI region and the single-threaded MERCI run were stopped before finishing: the first region already showed MERCI's behaviour, and each would have needed about ten more hours.

## Pool traffic

STREAM's copy and scale kernels sit just above a third of the peak, so three STREAM hosts would ask for more than the channel delivers. Its add and triad kernels move less data but are already queueing with one host: their latency is 660–720 ns, against about 405 ns for copy and scale. Those two kernels read two arrays and write a third, which likely costs more row misses and read-write switches in the single channel. Every other workload stays below 3 GB/s.

## Latency, requests in flight and core activity

Pool latency is the round trip seen by the host, including the 250 ns link. With no queueing it is about 240 ns.

| Workload | Pool latency (ns) | Requests in flight, average | Requests in flight, peak | Reads among requests | Busy cores (of 4) | Instructions per region |
| --- | --- | --- | --- | --- | --- | --- |
| STREAM copy and scale | 405–422 | 34 | 72–81 | about 2 in 3 | 3.8 | 31–37 M |
| STREAM add and triad | 662–717 | 48 | 97–100 | about 3 in 4 | 3.8 | 39–45 M |
| LLM decode | 283 | 15 | 60 | 99% | 3.9 | 717 M |
| GUPS | 239 | 3.4 | 16 | 50% | 4.0 | 764 M |
| bc | 283 | 9.6 | 94 | 92% | 3.8 | 130–150 M |
| MERCI (4 threads) | 236 | 4.2 | 52 | 98% | 4.0 | 492 M |
| vector search | 270 | 6.8 | 45 | 90% | 1.0 | 6–94 M per setting |
| multichase | 245 | 1.0 | 22 | 100% | 1.0 | 6 M |
| memcached | 273 | 2.9 | 23 | 83% | 1.0 | 913 M |

Only STREAM pushes pool latency above the unloaded level; every other workload sees an almost empty pool.

The requests-in-flight column follows from the simulated CPU. The gem5 timing CPU runs in order and waits for each memory access before the next instruction, so a core has at most one demand miss outstanding. Anything beyond one per core comes from the caches' stride prefetchers and from write-backs. That is why multichase holds exactly 1 request, MERCI and GUPS hold about one per core (4.2 and 3.4 with four cores), and STREAM, whose regular access pattern the prefetchers follow, holds 34–48.

Cores are busy almost all the time in every multi-threaded workload, and the single-threaded ones keep one core busy. So the guest's idle-loop setting cannot distort these results; the one workload with idle cores is memcached, whose server and client wait on each other.

## Caveats

1. **In-order cores limit random-access workloads.** The timing CPU keeps one demand miss per core in flight. A real out-of-order core keeps many, so on real hardware GUPS and MERCI would press the pool much harder than they do here. Workloads with regular access (STREAM, and partly the LLM and bc) recover parallelism through the prefetchers. gem5's out-of-order CPU model would fix this, at a much higher simulation cost.
2. **The LLM runs without vector instructions.** The simulated CPU reports only SSE3/SSSE3, so llama.cpp falls back to scalar code. Decode then becomes compute-heavy, whereas on real hardware it is limited by memory bandwidth. Its 2.7 GB/s understates what a real decode would draw.
3. **memcached's latency has a 1 ms step.** p50 is 0.015 ms but p90 and p99 sit at 1.0 ms in every region. This matches the guest's 1 ms timer tick and suggests that a sleeping core is not woken promptly in simulation. The cause is not proven, and a test with a polling idle loop made no progress. Its working set is also mostly cached (about 4 MB/s of pool traffic), and memtier's start-up falls inside the measured region.
4. **MERCI covers one region only.** Upstream MERCI also flushes the caches by writing a 48 MB buffer before every region. That write reaches the pool between regions, not inside them.
5. **Vector search has two changed size constants** so the hnswlib example fits the simulated memory. Its 46 regions differ in work: higher search-effort settings visit more of the graph and run longer.
6. **One host, so no fairness yet.** Phase 1 shows each workload's own demand.
