# Fairness Metrics for CXL Pooling

This document fixes which quantities the study measures, where each one comes from in the simulator, and why each is needed. It was written after the first 2-host runs. Two fixes to the simulator's gem5-to-SST bridge came out of it, and every later experiment uses them.

## Summary

- **Per-host measures from gem5:** run or kernel time, instructions, pool requests, and the mean and spread of pool round-trip latency. These give slowdown against an alone run, and from it every fairness index.
- **Pool measures from SST:** time a request spends inside the pool, queue length and controller busy cycles, for all hosts together.
- **Tail latency:** the bridge recorded every pool read's latency in a histogram of only 2 buckets of about 524 ns, so no percentile could be read. It was given fine buckets (5 ns from 0 to 2 µs), and later reports give per-host p95/p99 from it.
- **Write-tracking leak:** the bridge never removed writes from its request-tracking table. This leaked memory and made its "outstanding packets" statistic meaningless. It was fixed.
- **Per-host statistics at the pool** needed the pool to know each request's host. The scheduler's per-host front end (doc 12) provides this from the request's address slot.

## What a run records

Every run produces per-host statistics from gem5 (one `stats.txt` per host) and one set of pool statistics from SST for the whole run.

| Source | Statistic | Scope | What it gives |
| --- | --- | --- | --- |
| gem5, per host | `simSeconds` of each statistics dump | Per host, per dump | Elapsed simulated time, so rates and slowdown against an alone run |
| gem5, per host | committed instructions of all cores | Per host, per dump | Instruction rate, the main progress measure |
| gem5, per host | `outgoing_request_bridge.packetLatency` (mean, standard deviation, histogram) | Per host, per dump, every pool read | Round-trip latency of pool reads as the host sees it |
| gem5, per host | `numOutgoingPackets`, `numReadIncomingPackets` | Per host, per dump | Pool reads and writes, so per-host pool bandwidth and request rate |
| gem5, per host | `l3cache.demandAvgMissLatency` | Per host, per dump | Average L3 miss latency as the cores see it |
| SST, pool controller | `latency_GetS`, `latency_Write` (count, sum, sum of squares, min, max) | Whole run, all hosts together | Mean, standard deviation and maximum time a request spends inside the pool |
| SST, pool controller | `outstanding_requests` | Whole run | Average and maximum queue length at the pool |
| SST, pool controller | `cycles_with_issue`, `cycles_attempted_issue_but_rejected` | Whole run | How busy the controller is, and how often a full channel turned a request away |

The gem5 numbers are per host and per statistics period, so fairness can be computed for any span of the run. The stock SST numbers are for all hosts together, because the stock pool controller does not know which host sent a request.

## Latency percentiles

**What exists.** In `src/sst/external_memory.cc`, the bridge between a host and the pool stores the send time of each request and, when the response returns, records `now - send time` into `packetLatency`. That is the full round trip as the host sees it: CXL link delay + waiting at the pool + DRAM access.

**What limited it.** The histogram was created with `.init(2)`: two buckets, which gem5 widened to about 524 ns each to fit the largest value. In the 2-host Copy run, 98.5% of reads fell in the first bucket and 1.5% in the second, so no percentile could be read. The mean and standard deviation are computed from the exact samples and were already reliable.

**The fix.** `packetLatency` now has fixed buckets 5 ns wide from 0 to 2 µs (`.init(0, 2000000, 5000)` in ticks). Percentiles come from the cumulative bucket counts. Checkpoints stay valid, because statistics are not part of a checkpoint. The change is in `code/simulator_patches/src_sst_external_memory.cc.patch`.

The pool-side times (`latency_GetS`, `latency_Write`) stay as sums, so the pool reports a mean and maximum but no percentiles. Per-host pool-side counters come from the scheduler's front end instead (doc 12).

## Metric catalogue

| Metric | Definition | Source | Why it matters |
| --- | --- | --- | --- |
| Slowdown (per host) | progress alone ÷ progress shared, for the same host, checkpoint and span | gem5 dumps + alone run | The core quantity; 1.0 = unaffected by sharing |
| Highest slowdown | largest slowdown across the hosts of a mix | Derived | The worst-treated host; fairness schedulers aim to lower it |
| Unfairness | highest slowdown ÷ lowest slowdown | Derived | 1.0 = every host suffers equally |
| Jain's index | (Σx)² ÷ (n × Σx²) over per-host normalised progress x | Derived | Standard single-number fairness score; 1.0 = perfectly even |
| Weighted speedup | Σ (progress shared ÷ progress alone) over hosts | Derived | System throughput, so fairness gains are not bought with lost work; n = no loss |
| Harmonic speedup | n ÷ Σ slowdown | Derived | Balances throughput and fairness in one number |
| Per-host pool bandwidth | pool requests × 64 B ÷ time | gem5 bridge counters | Who gets what share of the pool |
| Pool round-trip latency (per host) | mean, standard deviation and percentiles of `packetLatency` | gem5 bridge | Shows queueing directly; the tail is what a latency-bound victim feels |
| Pool controller queueing | average and maximum waiting requests, mean and maximum time inside the pool, busy cycles | SST | Shows that a slowdown is queueing at the pool, not the fixed CXL link |
| Per-host queue occupancy and service | waiting and served requests per host at the pool | Scheduler front end | Direct evidence of who holds the shared queues |
| Bandwidth share over time | per-host bandwidth in 10 ms statistics periods | Periodic gem5 dumps | Shows bursts and phases that whole-run averages hide |
| Scheduler cost | state bits per host, logic per decision | Design analysis (doc 12) | Supports the claim that the mechanism fits in a device |

## How the metrics are used

Four questions decide whether a device-side scheduler helps. Each is answered against FCFS and FR-FCFS on the same checkpoints and the same pool.

1. **Victim protection.** Does the lightest host's slowdown fall, and how much does it cost the heavy hosts?
2. **Fairness.** Do the highest slowdown and the unfairness ratio fall?
3. **Throughput.** Does weighted speedup stay close to the baseline? A fairness scheme that costs a lot of throughput is easy to build; one that costs little is useful.
4. **No harm alone.** Does a host running alone behave exactly as under the baseline, so the scheduler costs nothing when there is nothing to fix?

The final comparison (doc 15) reports exactly these, each in its own column.

## Early result: two identical STREAM hosts

Sharing a 2-channel pool with one other STREAM host raised the host's mean pool read latency on three of the four STREAM kernels and widened its spread. The standard deviation of read latency rose from 62.5 to 77.0 ns on Scale and from 65.4 to 88.0 ns on Add, so the tail stretches faster than the mean. Kernel times rose 8.0% to 9.6% on Scale, Add and Triad, against 1.3% to 1.6% on Copy, and the two hosts stayed within 0.3% of each other. Inside the pool controller, mean time per read rose from 43.6 to 61.7 ns and the average queue from 1.9 to 4.9 requests.

## Two simulator issues found

Both are in CXL-ClusterSim's gem5-to-SST bridge (`src/sst/external_memory.cc`). Both are fixed in `code/simulator_patches/`.

| Issue | Evidence | Effect | Fix |
| --- | --- | --- | --- |
| Latency histogram has 2 buckets | `packetLatency.init(2)`; buckets of 0–524 ns and 524–1049 ns | No percentiles, so no tail latency | Fixed buckets of 5 ns from 0 to 2 µs |
| Writes are never removed from the request-tracking table | The table grew by about 1.05 M entries per kernel, exactly the number of writes; write responses received = 0; average table size 0.47 M, 1.5 M, 2.6 M and 3.6 M across the four kernels | A memory leak (host processes grew from about 3.7 GB to over 6 GB per run) and a meaningless `outstandingPackets` statistic | Remove an entry only if it exists, and free write-back packets and their tracking entries that SST never answers |

Neither issue changed the reported results: kernel times, bandwidth and the latency mean and spread come from other counters or from exact samples. Runs before and after the leak fix were bit-identical in every simulated statistic.
