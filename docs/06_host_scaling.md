# Host Scaling on a Shared CXL Pool

## Summary

On a 1-channel CXL pool, three identical STREAM hosts each slowed 1.26–1.37× (means of three runs) while staying within 1.8% of each other. On a 2-channel pool the same three hosts barely slowed (within ±1.4%, except Triad at +9%). Contention is real once the pool saturates, but identical hosts are treated fairly.

1. **Slowdown depends on whether the pool saturates.** Three hosts on 1 channel wanted more than the pool could deliver (about 8–9 GB/s together, about half of its 19.2 GB/s peak) and slowed 26–37%. On 2 channels they moved 13–15 GB/s without saturating and slowed at most 9%.
2. **Identical hosts are treated equally.** The slowest host was never more than 1.8% slower than the fastest with 2-core hosts on 1 channel (2.4% on 2 channels, 5.2% once with 4-core hosts), and Jain's index stayed at 0.9995 or higher.
3. **The cause is queueing inside the pool, not the CXL link.** On 1 channel, mean time per read inside the pool controller rose from 200 ns (alone) to 358 ns (3 hosts), and the average queue grew from 9.9 to 41.3 requests. On 2 channels it rose only from 45 to 56 ns. The fixed 250 ns link delay is the same in every run.
4. **At saturation the controller's DRAM queue is full most of the time.** With 3 hosts on 1 channel, the request at the head of the controller found the 32-entry DRAM queue full on 84% of cycles, against never when alone or on 2 channels.
5. **Four cores per host raise the slowdown, not the pressure.** Four cores make a host 1.26× faster alone but only 1.11× faster when sharing, so Copy's slowdown rises from 1.37× to 1.79×. Each host keeps at most about 20 requests in flight either way, the limit of its L3 cache.

This is the symmetric control experiment. It shows that contention exists and is measurable, and that FCFS stays fair when every host behaves the same; the fairness question proper needs unequal hosts (aggressor and victim), which doc 05 covers.

## Setup

Six experiments ran in several cluster jobs, each host running the same STREAM workload in its own 1 GiB pool slice. The 1-channel experiments with 2-core hosts were run three times from freshly booted checkpoints; the others were run once.

| Experiment | Hosts | Cores per host | Pool | Runs | Purpose |
| --- | --- | --- | --- | --- | --- |
| Alone | 1 | 2 | 1 channel | 3 | Baseline: each kernel's time with no other host |
| 3 hosts | 3 | 2 | 1 channel | 3 | Contention on a pool that saturates |
| Alone, 2 channels | 1 | 2 | 2 channels | 1 | Baseline for the 2-channel pool |
| 3 hosts, 2 channels | 3 | 2 | 2 channels | 1 | Contention below saturation |
| Alone, 4 cores | 1 | 4 | 1 channel | 1 | Baseline for 4-core hosts |
| 3 hosts, 4 cores | 3 | 4 | 1 channel | 1 | Whether more cores per host change the picture |

- **Simulator:** CXL-ClusterSim (gem5 hosts + SST pool). Each host: x86 with 2 or 4 cores at 3 GHz, timing CPU in the measured region, 32 KiB L1, 512 KiB L2, 8 MiB L3, 1 GiB local DDR4.
- **Pool:** SST `MemController` (1.2 GHz, 64 B per cycle) with a `timingDRAM` backend of 1 or 2 channels × 2 ranks × 16 banks, 19.2 GB/s peak per channel; 250 ns link delay; requests scheduled first-come first-served per bank.
- **Workload:** STREAM with 8,388,608 elements (64 MiB per array, 192 MiB in total), one OpenMP thread per core, bound to the pool with `numactl --membind=1`. Each host measures four kernels: Copy, Scale (2 arrays), Add and Triad (3 arrays).
- **Kernel selection:** each kernel's statistics are taken from the stats dump whose end tick equals that kernel's `workend` event, so duplicate and extra dumps are ignored.
- **Slowdown:** a host's kernel time divided by the same kernel's time in the Alone run with the same pool and core count (for 1 channel and 2 cores, the mean of the three alone runs). Jain's index is computed over each host's normalised performance (1 / slowdown); weighted speedup is the sum of those values (ideal = number of hosts); harmonic speedup is hosts divided by the sum of slowdowns (ideal = 1).

## How realistic the simulated pool is

Each simulated pool channel is DDR4-2400 at 19.2 GB/s. The 2-channel pool's 38.4 GB/s theoretical peak is in the same class as today's typical single CXL memory expanders, which vendors rate at up to 36 GB/s measured; the 1-channel pool is a smaller, cost-optimised device.

| Device | Interface | Bandwidth (vendor figure) |
| --- | --- | --- |
| [Micron CZ120](https://www.tomshardware.com/news/micron-unveils-128gb-256gb-cxl-2-expansion-modules) | CXL 2.0, PCIe 5.0 x8 | Up to 36 GB/s, measured with Intel MLC at a 2:1 read/write ratio |
| [Samsung CMM-D](https://semiconductor.samsung.com/cxl-memory/cmm-d/md220/mxfah1280mb0-ccp) | CXL 2.0, PCIe 5.0 | Up to 36 GB/s |
| [Astera Labs Leo](https://www.asteralabs.com/solutions/general-purpose-servers/memory-expansion/) (controller) | CXL, up to x16 | Up to 89.6 GB/s memory bandwidth |
| Simulated pool (this study) | 1 or 2 channels × DDR4-2400 | 19.2 or 38.4 GB/s theoretical peak |

For reference, a PCIe 5.0 x8 link carries about 32 GB/s in each direction and an x16 link about 64 GB/s.

- **Peak versus achievable.** 38.4 GB/s is a theoretical peak (2,400 M transfers/s × 8 bytes × 2 channels). Real DRAM controllers typically sustain 70–85% of peak. The simulated pool sustains less: with 3 hosts the 1-channel pool delivered about 8–9 GB/s, about half of its 19.2 GB/s peak, because its banks serve requests strictly in arrival order and its DRAM queue holds 32 requests. In peak terms two channels model a single x8 CXL 2.0 expander, the most common device today; in delivered bandwidth the simulated pool is closer to half of one.
- **Other channel counts.** One channel (19.2 GB/s) represents a cost-optimised device or a small backend shared by many hosts; four channels (76.8 GB/s, the CXL-ClusterSim default) exceed what an x16 link can carry and resemble a high-end controller such as Leo.
- **The CXL link has a delay but no bandwidth limit in the model.** On real hardware the x8 link is a second possible bottleneck. In multi-host pooling each host has its own link and the DRAM behind the device is shared, so the shared DRAM is the contention point that matters for fairness, and that is what the model captures.
- **DDR4 channels versus DDR5.** Real devices use DDR5, whose single channel gives about 38-45 GB/s, so they reach 36 GB/s with fewer, faster channels. Total bandwidth, which sets the contention, is in the same range.

## Slowdown from sharing

Sharing the 1-channel pool slowed every kernel, by 26–37% with 2-core hosts and by 27–79% with 4-core hosts. On 2 channels the same three hosts stayed within 1.4% of their alone times, except Triad (+9%).

Copy and Scale, which move two arrays, suffer most on 1 channel, and most of all with 4-core hosts, whose alone runs are the fastest. The 2-channel Add value (−1.0%) is run-to-run variation: a host cannot speed up by sharing, and even STREAM alone varies by up to 12% between runs. Within a run the whiskers are narrow, so every host paid about the same price; for 1 channel with 2 cores they are wider because they span three runs.

## Fairness between hosts

With identical workloads, first-come first-served shared the pool almost evenly: within any run the slowest host was never more than 1.8% slower than the fastest with 2-core hosts on 1 channel (2.4% on 2 channels, 5.2% with 4-core hosts), and Jain's index never fell below 0.9995.

| Experiment | Kernel | Slowdown range across hosts | Slowest ÷ fastest | Jain's index | Weighted speedup (ideal) | Harmonic speedup |
| --- | --- | --- | --- | --- | --- | --- |
| 3 hosts (3 runs) | Copy | +27.1% to +43.9% | 1.0174 | 0.9999 | 2.194 (3) | 0.731 |
| 3 hosts (3 runs) | Scale | +31.2% to +36.9% | 1.0182 | 0.9999 | 2.248 (3) | 0.749 |
| 3 hosts (3 runs) | Add | +26.9% to +37.3% | 1.0117 | 1.0000 | 2.284 (3) | 0.761 |
| 3 hosts (3 runs) | Triad | +19.0% to +34.4% | 1.0151 | 1.0000 | 2.386 (3) | 0.795 |
| 3 hosts, 2 channels | Copy | −0.3% to +1.2% | 1.0150 | 1.0000 | 2.980 (3) | 0.993 |
| 3 hosts, 2 channels | Scale | +0.5% to +3.0% | 1.0244 | 0.9999 | 2.960 (3) | 0.986 |
| 3 hosts, 2 channels | Add | −1.6% to 0.0% | 1.0165 | 0.9999 | 3.031 (3) | 1.010 |
| 3 hosts, 2 channels | Triad | +8.9% to +9.3% | 1.0028 | 1.0000 | 2.751 (3) | 0.917 |
| 3 hosts, 4 cores | Copy | +76.3% to +80.4% | 1.0232 | 0.9999 | 1.678 (3) | 0.559 |
| 3 hosts, 4 cores | Scale | +66.0% to +71.3% | 1.0323 | 0.9998 | 1.784 (3) | 0.594 |
| 3 hosts, 4 cores | Add | +40.8% to +48.1% | 1.0517 | 0.9995 | 2.063 (3) | 0.687 |
| 3 hosts, 4 cores | Triad | +26.3% to +28.7% | 1.0187 | 0.9999 | 2.359 (3) | 0.786 |

- **Throughput loss is the visible cost.** On 1 channel, three hosts together did 73–80% of the work they would do with the pool to themselves (weighted speedup 2.19–2.39 out of 3), and 56–79% with 4-core hosts. On 2 channels they did about 92–100%.
- **No host was consistently favoured.** Which host was slowest changed from kernel to kernel and from run to run (each of the three hosts was slowest at least once), so the small spread is noise, not bias.
- **Runs differ more than hosts.** For the three 1-channel runs, slowest ÷ fastest and Jain's index are the worst single run, and the slowdown range spans all hosts of all three runs. Within a run hosts stay within 1.8%, but a kernel's slowdown can differ by up to 0.17 between runs (Copy 1.27–1.44).

## Pool latency seen by the hosts

The round-trip time of a pool read, measured at each host, rose by 134–170 ns on average with 3 hosts on 1 channel, and its p99 rose faster than its mean: the slowest requests stretch most. On 2 channels it barely moved.

Mean / p99 pool read latency, averaged over the hosts of each run (responses under 100 ns, a bridge artefact, excluded):

| Kernel | Alone | 3 hosts | Alone, 2 channels | 3 hosts, 2 channels | Alone, 4 cores | 3 hosts, 4 cores |
| --- | --- | --- | --- | --- | --- | --- |
| Copy | 377 / 567 ns | 546 / 1,132 ns | 297 / 475 ns | 304 / 472 ns | 302 / 480 ns | 572 / 1,515 ns |
| Scale | 381 / 593 ns | 533 / 1,081 ns | 298 / 470 ns | 306 / 492 ns | 339 / 880 ns | 597 / 1,440 ns |
| Add | 496 / 983 ns | 661 / 1,375 ns | 295 / 405 ns | 295 / 453 ns | 389 / 995 ns | 574 / 1,738 ns |
| Triad | 481 / 952 ns | 615 / 1,170 ns | 282 / 365 ns | 307 / 545 ns | 427 / 955 ns | 548 / 1,577 ns |

- On Copy (1 channel, 2 cores), the mean rose 45% (377 to 546 ns) but p99 doubled (567 to 1,132 ns).
- With 4-core hosts, p99 rose 1.6–3.2×, to 1.4–1.7 µs.

## Inside the pool controller

The pool's own statistics locate the slowdown: on 1 channel, each read spent 1.8× as long in the controller with 3 hosts as alone, the queue quadrupled, and the DRAM queue was full on most cycles. On 2 channels the controller stayed far from that.

| Statistic (whole run, all hosts) | Alone | 3 hosts | Alone, 2 channels | 3 hosts, 2 channels | Alone, 4 cores | 3 hosts, 4 cores |
| --- | --- | --- | --- | --- | --- | --- |
| Reads / writes served | 10.5 M / 4.2 M | 31.5 M / 12.5 M | 10.5 M / 4.2 M | 31.5 M / 12.5 M | 10.5 M / 4.2 M | 31.6 M / 12.6 M |
| Mean read time in controller | 200.2 ns | 357.6 ns | 44.9 ns | 55.6 ns | 126.5 ns | 328.3 ns |
| Standard deviation of that time | 155.8 ns | 226.7 ns | 34.6 ns | 47.5 ns | 171.9 ns | 300.8 ns |
| Slowest single read in controller | 1,083 ns | 2,297 ns | 543 ns | 1,382 ns | 1,017 ns | 5,700 ns |
| Mean write time in controller | 189.0 ns | 346.7 ns | 38.3 ns | 47.1 ns | 116.0 ns | 330.9 ns |
| Average / maximum requests waiting | 9.9 / 49 | 41.3 / 180 | 2.9 / 50 | 10.6 / 89 | 7.8 / 77 | 42.7 / 141 |
| Cycles the DRAM queue was full | 0% | 84% | 0% | under 0.01% | 0% | 82% |

The Alone and 3 hosts columns (1 channel, 2 cores) are means of three runs; maxima are the largest of the three.

- **Queueing, not the link.** Time inside the pool rose by 157 ns from alone to 3 hosts on 1 channel, with the link delay unchanged. That accounts for nearly all of the 134–170 ns rise the hosts saw.
- **The DRAM queue is the bottleneck.** On 1 channel the controller's 32-entry DRAM queue was full on 82–84% of cycles with 3 hosts, so delivered bandwidth stopped at about 8–9 GB/s, about half of the 19.2 GB/s peak. On 2 channels it was full on under 0.01% of cycles.
- **The worst case grows fastest.** On 1 channel the slowest single read went from 1,083 to 2,297 ns (5,700 ns with 4-core hosts), while the mean grew 1.8×: the tail is where a latency-sensitive neighbour would suffer.

## Four cores per host versus two

Doubling the cores per host made STREAM 1.26× faster alone but only 1.11× faster when three hosts shared the 1-channel pool, so the slowdown rose. Total pool traffic, the controller's queue and its latency stayed about the same.

| Kernel | Alone, 2 cores | Alone, 4 cores | 3 hosts, 2 cores | 3 hosts, 4 cores | Slowdown, 2 → 4 cores |
| --- | --- | --- | --- | --- | --- |
| Copy | 51.51 ms | 36.15 ms | 70.59 ms | 64.63 ms | 1.37 → 1.79 |
| Scale | 52.31 ms | 39.91 ms | 69.82 ms | 67.14 ms | 1.34 → 1.68 |
| Add | 84.47 ms | 65.95 ms | 111.06 ms | 95.94 ms | 1.32 → 1.46 |
| Triad | 82.21 ms | 71.97 ms | 103.58 ms | 91.53 ms | 1.26 → 1.27 |

The measured region runs on gem5's timing CPU, which waits on each cache miss, so a host's requests in flight come mostly from the hardware prefetchers. They are capped by the shared L3 cache, which can track 20 outstanding misses: 2-core hosts already kept 16–19 requests in flight, and 4-core hosts 19.5. Alone, the extra cores let a host use more of a lightly loaded pool. Shared, the pool's DRAM queue is the limit either way, so three hosts delivered about the same total (Copy and Scale 9.0–9.2 GB/s with 4 cores, against 8.1–9.0 GB/s with 2). Mean kernel times are 2-core means of three runs and 4-core single runs.

## Methodology notes and simulation cost

The results are clean, but a few things about how these runs were made are worth recording.

| Experiment | Real time to finish | Simulated kernel time per host |
| --- | --- | --- |
| Alone | 2 h 10–12 min | about 271 ms |
| 3 hosts | 5 h 12 min – 6 h 4 min | about 355 ms |
| Alone, 2 channels | 1 h 52 min | about 195 ms |
| 3 hosts, 2 channels | 4 h 2 min | about 200 ms |
| Alone, 4 cores | 2 h 4 min | about 214 ms |
| 3 hosts, 4 cores | 5 h 46 min | about 319 ms |

- **Simulation speed does not affect results.** Simulated times are computed, not measured with a clock, so how fast the cluster ran changes only the real time above.
- **Repeats need fresh checkpoints.** The simulator is deterministic, so rerunning the same checkpoint gives the same result. The three 1-channel runs with 2-core hosts each restored from separately booted checkpoints.
- **Extra and duplicate stats dumps.** Every kernel appears in two dumps (the gem5-SST bridge dumps on `workend` without resetting, then STREAM dumps again). Each kernel was taken from the one dump whose end tick matches its `workend` event; the others were ignored, and none of the counters were altered.
- **Latency percentiles.** Each host's pool read latency comes from histograms at the gem5-SST bridge. About 2–3% of responses return in under 100 ns, a bridge artefact, and are excluded.
- **Earlier batch replaced.** An earlier version of this page reported a batch in which every host ran on one CPU, whatever its core count, because of a guest boot issue. That is fixed, and all numbers here come from multi-core hosts.
- **Checkpoints.** Each host restored from a boot checkpoint taken on a desktop with KVM, so the measured region starts right after STREAM's setup; only the measured kernels ran in the detailed simulation.
