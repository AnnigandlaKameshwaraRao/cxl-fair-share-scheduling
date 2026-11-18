# Saturating the CXL Pool: Multi-Core Hosts and FCFS Unfairness

Once the CXL pool saturates, FCFS makes a light, latency-bound host slow down 1.49× while it sends only about 2% of the traffic. That is as much as, or more than, the bandwidth-heavy hosts that cause the congestion.

## Summary

- **The victim is hurt most at saturation.** With 3 STREAM hosts (2 threads each) and a multichase victim on a 1-channel pool, the victim slowed **1.49×**. Its p99 latency more than doubled (460 → 1015 ns) and its p99.9 almost tripled (505 → 1410 ns). The STREAM hosts slowed 1.22–1.48×. On a 2-channel pool the same workload is close to fair: the victim slows only 1.02×. Three independent runs on the 1-channel pool give a victim slowdown of 1.49 ± 0.04.
- **FCFS is fair between equals and unfair between unequal hosts.** The 3 identical STREAM hosts slowed within 0.4–1.2% of each other (Jain = 1.0000). FCFS hands out capacity in proportion to requests in flight, so the victim, with 1 request in flight against about 18 for each STREAM host, gets about 2% of the queue positions.
- **Every nanosecond of the victim's extra delay comes from others.** It waits about **133 ns more per load** (a third of its round trip). Each STREAM host already waited 125–255 ns behind its own requests before anyone else arrived.
- **Interference runs one way even at moderate load.** With 1 STREAM host and the victim, STREAM barely notices the victim (+0.7–0.8% latency in 3 of 4 kernels), while the victim's p99.9 nearly doubles (505 → 955 ns).
- **The pool saturates far below its peak.** The 1-channel pool delivered at most about **8 GB/s of its 19.2 GB/s peak**: row misses (30 ns each), FIFO bank queues and a 32-entry DRAM queue limit it. Queues grew from 0.08 to 42 requests on average.
- **Jain's index hides the problem.** With the victim included, Jain stays at 0.994–1.000 because every host slowed. Slowdown measured against each host's share of traffic, max/min slowdown and the victim's tail latency show the unfairness that Jain misses.
- **Simulated hosts are now really multi-core.** Three x86 boot issues had kept every simulated host on a single CPU. All three are fixed; earlier results stand as single-CPU hosts.

## Making the hosts multi-core

Every simulated host had been running on one CPU, whatever core count it was given; three x86 issues caused it, and all three are now fixed. The guest kernel reported `nr_cpu_ids:1` and "Total of 1 processors activated", and the second core recorded 0 cycles in every stats dump. That is also why giving hosts 4 cores had made no difference earlier.

| Issue | Where | Symptom | Fix |
| --- | --- | --- | --- |
| CPUs missing from the ACPI table | Board setup (`X86ComposableMemoryBoard`) | The board listed both CPUs in the old MP table but none in the ACPI MADT. Linux 6.9 reads the MADT, so it found only the boot CPU. | Add one `X86ACPIMadtLAPIC` entry per core, as gem5's own x86 board does |
| Boot CPU not flagged as such | gem5 KVM CPU (`updateKvmStateSRegs`) | APICBASE was copied to KVM with `readMiscRegNoEffect`, which skips setting the BSP bit. Linux 6.9+ then assumes a crash kernel and limits itself to one CPU. | Copy APICBASE with `readMiscReg`, which sets the BSP bit for core 0 |
| Idle core panics | gem5 timing CPU, `mwait` idle loop | With 2 CPUs and a single-threaded victim, the second CPU goes idle. Its `mwait` idle loop page-faults under the timing CPU and the guest kernel panics. | Boot with `idle=halt`, so idle CPUs use `hlt` |

**Why the original authors would not have seen these.** CXL-ClusterSim's own experiments use ARM and RISC-V with a Linux 5.4 kernel. The x86 path met a newer kernel (6.9.9) only in this project. Linux 5.4 falls back to the MP table and does not check the BSP bit. Their headline result also varies the number of hosts, not cores per host.

**Why the `mwait` crash never appeared before.** On one CPU, the CPU was never idle during the measured part: multichase's chase thread and STREAM keep it 100% busy. The guest did idle during boot, but boot runs under KVM on the real processor, where `mwait` works.

**What it means for earlier results.** They stay valid as single-CPU hosts. STREAM ran one thread, and multichase is single-threaded anyway. What the issues blocked was multi-core hosts, which are needed for each aggressor to produce server-like traffic.

With the fixes, every checkpoint boots with 2 CPUs. In the STREAM hosts, both cores executed about the same number of instructions (about 9.1M each in the first interval checked).

## Experiment design

Four hosts share one pool device in the main experiment, matching how many hosts a single pool device serves in Octopus-style CXL designs. The pool runs plain FCFS, the baseline for the schedulers of doc 12.

**Why 4 hosts.** In [Octopus](https://arxiv.org/html/2501.09020v3) (Microsoft Azure, UW and Columbia; [NSDI '26](https://www.usenix.org/conference/nsdi26/presentation/zhong)), hosts connect directly to small multi-headed pool devices with few ports, for example 4, with no CXL switch. Each host connects to several devices, and the pod as a whole can be large. A device's memory controller, where our scheduler sits, still only arbitrates between the hosts plugged into it: about 4, at most 8. Real servers have dozens of cores, so 4 of them can saturate a device; our 2-core simulated hosts need more threads per host to do the same.

| Experiment | Hosts | What it isolates |
| --- | --- | --- |
| Victim alone | multichase | Victim baseline |
| STREAM alone | STREAM, 2 threads | Aggressor baseline |
| 1 STREAM + victim | STREAM + multichase | Moderate load |
| 3 STREAM + victim | 3 × STREAM + multichase | Saturated pool |

All four were run on a 1-channel pool. The same four were then repeated on a 2-channel pool (38.4 GB/s peak) from the same checkpoints, so the channel count is the only difference.

| Setting | Value |
| --- | --- |
| Host CPU | 2 cores at 3 GHz, timing CPU in the measured region; L1 32 KiB, L2 512 KiB, L3 8 MiB |
| Victim | Google multichase, `-m 256m`, single-threaded pointer chase, 25 ms samples |
| Aggressor | STREAM (OpenMP build), `OMP_NUM_THREADS=2`, 8,388,608 elements per array |
| Placement | `numactl --membind=1`, so all data lives in the pool |
| Pool | SST `memHierarchy.MemController` at 1.2 GHz with a `timingDRAM` backend (per-bank FIFO queues), DDR4-2400-like, 1 channel = 19.2 GB/s peak |
| CXL link | 250 ns, applied on responses |
| Pool capacity | 1 GiB slot per host, so 4 GiB for 4 hosts; same for any channel count |

The benchmarks are unmodified upstream code plus the standard gem5 region-of-interest markers (`m5 resetstats`, `workbegin`, `workend`, `dumpresetstats`). Each measured interval is one STREAM kernel, or multichase's whole sampling run after its first sample is dropped.

## Victim results

The victim slowed 1.04× next to 1 STREAM host and **1.49× next to 3**, and the slowdown is concentrated in its tail. multichase runs for a fixed time, so a slowdown shows up as fewer loads completed in that time.

| Run (1-channel pool) | Time per load | Loads in 288 ms | Slowdown | Mean pool latency | Extra wait per load |
| --- | --- | --- | --- | --- | --- |
| Victim alone | 273.7 ns | 1,050,597 | 1.00 | 252.7 ns | 0 (reference) |
| + 1 STREAM | 283.7 ns | 1,013,564 | 1.04 | 262.9 ns | +10.2 ns (4%) |
| + 3 STREAM | 406.5 ns | 709,717 | **1.49** | 385.7 ns | **+133.0 ns (34% of its round trip)** |

Pool latency is measured at each host's gem5–SST bridge, excluding responses under 100 ns. Those are a known simulator artefact, about 2–3% of reads.

**The victim's average queue time.** Alone, the pool queue is essentially empty (0.08 requests on average), so the victim's round trip is link delay plus DRAM service. Whatever the mixed runs add is time lost to other hosts: **about 133 ns per load with 3 STREAM hosts**, about half the 250 ns CXL link delay again. Part of it is longer DRAM service rather than queueing: other hosts keep closing the rows the victim's requests need, turning more of its accesses into 30 ns row misses. The two cannot be separated from the host side.

The median moves only from 250 to 350 ns, while p99 more than doubles and p99.9 nearly triples. With 1 STREAM host the mean barely moves, but p99.9 already nearly doubles.

## STREAM aggressors and fairness among them

The 3 STREAM hosts slowed 1.22–1.48×, and by almost exactly the same amount as each other. Slowdowns are against STREAM (2 threads) alone on the same 1-channel pool, whose kernels took 52.2 / 52.5 / 87.2 / 83.6 ms (Copy / Scale / Add / Triad) at 3.1–3.85 GB/s.

| Kernel | Slowdown, + victim only | Slowdown, 3 STREAM + victim (host 0 / 1 / 2) | Max/min across STREAM hosts | Bandwidth per STREAM host |
| --- | --- | --- | --- | --- |
| Copy | 1.00 | 1.480 / 1.474 / 1.476 | 1.004 | 2.57–2.58 GB/s |
| Scale | 1.01 | 1.349 / 1.333 / 1.340 | 1.012 | 2.85–2.88 GB/s |
| Add | 1.06 | 1.251 / 1.247 / 1.250 | 1.003 | 2.47–2.48 GB/s |
| Triad | 1.01 | 1.228 / 1.225 / 1.216 | 1.010 | 2.62–2.65 GB/s |

Total kernel time per STREAM host was 359.7 / 358.1 / 358.0 ms, within 0.5%. Jain's index across the 3 STREAM hosts is 1.0000 for every kernel.

**Why FCFS is fair here.** FCFS gives each host a share of the pool in proportion to the requests it has waiting. Identical hosts keep the same number in flight (about 17–19 each), so they get identical shares. This matches the earlier symmetric STREAM controls (Jain ≈ 1). FCFS is fair between equal hosts and unfair between hosts that behave differently.

**How 2 threads work.** Each STREAM host runs one STREAM process whose kernels are OpenMP `parallel for` loops. Both threads run the same kernel at the same time, each on half the arrays, and wait for each other at the end of the loop before the next kernel starts. Each host moves the same data as with one thread, but keeps about 17–19 requests in flight instead of 9–11.

## Why the pool saturated at about 8 GB/s

The 3 STREAM hosts wanted far more than 8 GB/s, but the 1-channel pool could deliver no more. Each host then slowed down to match.

**Demand is closed-loop.** Each STREAM host keeps a roughly fixed number of requests in flight, so its bandwidth follows Little's law:

**host bandwidth ≈ (requests in flight × 64 B) / round-trip latency**

The estimate of 16 GB/s assumed the round trip stayed near 215 ns, about 5 GB/s per host. Instead, latency rose with load and bandwidth per host fell. Below saturation, more requests in flight buy more bandwidth. At saturation, extra requests in flight only add waiting time.

| Regime | Run | Requests in flight per STREAM host | Bandwidth per STREAM host | STREAM pool latency | Controller queue (avg) |
| --- | --- | --- | --- | --- | --- |
| Below saturation | STREAM alone, 1 thread, 2-channel pool (earlier batch) | 8.7–11.4 | 2.8–3.1 GB/s | about 215 ns (from Little's law) | 1.9 |
| Approaching | STREAM alone, 2 threads, 1-channel pool | 16.3–19.2 | 3.1–3.85 GB/s | 378–510 ns | 10.1 |
| Saturated | 3 STREAM + victim, 1-channel pool | 17.0–19.4 | 2.47–2.88 GB/s (about 8 GB/s in total) | 537–649 ns | 42.2 |

About 1.8× the requests in flight bought only about 1.3× the bandwidth on the way to saturation; at saturation, total throughput stopped at about 8 GB/s. A rough check: about 55 requests in flight (3 × 18 + 1) ÷ about 125 M lines/s gives about 440 ns, close to the measured round trips once the link delay and the writes (which use capacity but are not in-flight reads) are counted.

**Why usable capacity is about 8 GB/s, not 19.2.** 19.2 GB/s is the peak transfer rate: a 64 B transfer every 4 DRAM cycles, back to back, every access hitting an open row. The pool's `timingDRAM` model is less forgiving:

- **Row misses are expensive:** precharge 14 + activate 11 + column read 11 = 36 cycles (30 ns), against 4 cycles to transfer the data. Rows are 1 KiB.
- **About 13 interleaved streams** (3 hosts × 2 threads × 2–3 arrays, plus the victim's random loads) keep closing each other's rows.
- **Banks serve requests strictly in arrival order (FIFO).** A request that would hit the open row cannot overtake one that misses. Real controllers reorder for row hits (FR-FCFS) and typically reach 60–80% of peak.
- **The controller-to-DRAM queue holds 32 requests and was full almost all the time:** 393 million cycles in which the controller had a request ready and the DRAM could not take it. The controller's average queue was 42 (max 134), against 0.08 for the victim alone.

Even STREAM alone with 2 threads queued (average 10) at about 20% of peak. Row-hit rates were not measured, so the row-conflict explanation is likely but was not confirmed here. The FIFO bank queue (`fifoTransactionQ`) is where the fair scheduler plugs in, so the contention measured here sits at the enforcement point.

**How addresses reach channels.** The pool's address mapper deals 64 B lines out like cards: line = address / 64, channel = aline mod channels, bank = (line / channels) mod banks. With 2 channels, alternate lines go to alternate channels; with 1 channel, every line goes to channel 0. Hosts never share an address (each has its own 1 GiB slot), but host 0's line 1000 and host 2's line 1000 land on the same channel and bank in different rows. Contention is for channels, banks and the controller queue, not for addresses.

**Pool capacity.** The pool's address range ends at 8 GiB for 4 hosts: an unused range below 4 GiB, where each host's local memory and I/O space sit, then one 1 GiB slot per host. Usable capacity is hosts × 1 GiB, whatever the channel count. STREAM uses about 192 MiB of its slot (3 arrays × 8,388,608 doubles), multichase 256 MiB. In real hardware, adding a channel usually adds capacity too; in this model the two are independent, so channel count changes only bandwidth and bank parallelism.

## Who delays whom

All of the victim's extra latency is caused by other hosts, while a STREAM host was already waiting behind its own requests before anyone else arrived. The victim also turns added latency one-for-one into slowdown, which STREAM does not.

### Saturated: 3 STREAM + victim

Mean pool round trip per load; the STREAM column with others is the average of the 3 hosts.

| Host / kernel | Alone | With the others | Added by the others | p99 alone → with others |
| --- | --- | --- | --- | --- |
| STREAM Copy | 378.4 ns | 601.9 ns | +223.5 ns (+59%) | 575 → about 1,195 ns |
| STREAM Scale | 380.4 ns | 538.1 ns | +157.7 ns (+41%) | 580 → about 1,090 ns |
| STREAM Add | 510.2 ns | 647.5 ns | +137.3 ns (+27%) | 970 → about 1,350 ns |
| STREAM Triad | 488.4 ns | 606.2 ns | +117.8 ns (+24%) | 960 → about 1,230 ns |
| **Victim** | 252.7 ns | 385.7 ns | **+133.0 ns (+53%)** | 460 → 1,015 ns |

- **STREAM was already queueing alone; the victim wasn't.** The victim alone gets the uncontended round trip, about 253 ns. STREAM alone sits at 378–510 ns, so each STREAM host waits about 125–255 ns behind its own 17–19 requests. Add and Triad (3 arrays) queue most on their own, so the others add relatively less to them.
- **Every nanosecond of the victim's increase comes from others.** With one request in flight, it never waits behind itself. The others add +133 ns, a larger relative increase (+53%) than for Scale, Add or Triad.
- **The same delay costs the victim more.** Each victim load must finish before the next starts, so its run time scales with latency: about +50% latency gives its 1.49× slowdown. STREAM overlaps about 18 requests, and its slowdown (1.22–1.48×) depends on the bandwidth it gets, including its writes and the full controller queue.

### Moderate load: 1 STREAM + victim

| Host / kernel | Alone | Together | Change | p99.9 alone → together |
| --- | --- | --- | --- | --- |
| STREAM Copy | 378.4 ns | 381.2 ns | +2.8 ns (+0.7%) | 860 → 735 ns |
| STREAM Scale | 380.4 ns | 383.0 ns | +2.6 ns (+0.7%) | 875 → 900 ns |
| STREAM Add | 510.2 ns | 542.0 ns | +31.8 ns (+6.2%) | 1,060 → 1,110 ns |
| STREAM Triad | 488.4 ns | 492.3 ns | +3.9 ns (+0.8%) | 1,060 → 1,065 ns |
| **Victim** | 252.7 ns | 262.9 ns | **+10.2 ns (+4.0%)** | **505 → 955 ns** |

The victim sends about 0.23 GB/s with one request in flight, about 6% of STREAM's request rate, so it is almost never ahead of STREAM in the queue. STREAM, in contrast, nearly doubles the victim's p99.9: most victim loads find a short queue, but one that lands during a STREAM burst waits behind up to about 18 requests.

**One anomaly.** STREAM's Add got 31.8 ns slower next to the victim (+6.2%; its run time rose 5.8%), well above the usual noise floor of about ±0.1%. Copy, Scale and Triad did not change. The same experiment on a 2-channel pool shows the opposite: Add ran 5.1% faster next to the victim and Triad 2.6% slower, while Copy and Scale moved by under 0.7%. A victim cannot speed STREAM up, so this is most likely run-to-run variation of about ±5% in the 2-thread Add and Triad kernels, not interference. Instruction counts per core are the same in every run, so the variation is in timing, not in work done. The three independent runs in the Repeatability section confirm this.

## Fairness metrics: what Jain's index misses

Jain's index on slowdowns rates the saturated run as fair (0.994–1.000 with the victim included) because every host slowed by 1.2–1.5×. It cannot see that the victim pays as much as the hosts causing the congestion while barely contributing to it.

**J = (Σ xᵢ)² / (n · Σ xᵢ²)**, where xᵢ = 1 / slowdownᵢ and n is the number of hosts. J = 1 means equal treatment; J = 1/n means one host gets everything.

|  | Each STREAM host | Victim |
| --- | --- | --- |
| Share of pool traffic | about 33% | about 2% |
| Requests in flight | about 17–19 | 1 |
| Slowdown | 1.22–1.48× | 1.49× |
| p99.9 latency, alone → shared | 860–1,060 → 1,255–1,690 ns | 505 → 1,410 ns (2.8×) |

**Metrics that show the problem:**

- **Max/min slowdown including the victim:** 1.485 / 1.216 = 1.22 during Triad.
- **Slowdown against share of traffic,** or the slowdown of hosts using less than their fair share (a quarter of the pool with 4 hosts). A fair-share design should leave such a host close to 1.0×.
- **The victim's tail latency** (p99, p99.9), where interference shows before the mean moves.

Jain's index is therefore reported alongside these, so that "Jain ≈ 1" is not read as "fair".

**Why FCFS produces this.** At saturation, FCFS gives each host queue positions in proportion to its requests waiting: about 18 of about 55 for each STREAM host, 1 of about 55 for the victim. The victim cannot ask harder, because each load depends on the previous one. A fair-share scheduler at the pool's bank queues would limit how much of the queue one host can occupy, or let a host far below its share go first. The aggressors are throughput-bound and would lose little.

## Comparison with the earlier single-CPU batch

The same 3 STREAM + victim mix gave the victim only a 1.01× slowdown in the earlier batch, because that run sent about half the traffic into twice the channel capacity.

|  | Earlier batch | This batch |
| --- | --- | --- |
| Pool | 2 channels (38.4 GB/s peak) | 1 channel (19.2 GB/s peak) |
| STREAM threads per host | 1 (the guests had one CPU) | 2 |
| Requests in flight per STREAM host | about 9–11 | about 17–19 |
| Interleaved access streams | about 7 | about 13 |
| Total pool traffic | about 8.5 GB/s (22% of peak) | about 8 GB/s (the saturation point) |
| Controller queue, avg / max | 7.6 / 72 | 42.2 / 134 |
| Cycles with the DRAM queue full | 24 thousand | 393 million |
| STREAM slowdown | 1.04–1.10× | 1.22–1.48× |
| Victim slowdown | 1.01× | 1.49× |
| Victim mean / p99.9 latency (alone 252.6 / 505 ns) | 255.6 / 530 ns | 385.7 / 1,410 ns |

At about a quarter of peak, FCFS did not starve the light host: the cost of sharing fell mostly on the heavy hosts, which queued behind each other. Strong victim unfairness appears only once the pool saturates. The 2-channel repeat below separates the channel effect from the effect of the second thread.

## One channel versus two

On a 2-channel pool the same 3 STREAM + victim workload is close to fair: the victim slows only 1.02× and the STREAM hosts at most 1.06×. The FCFS victim penalty appears only once the pool saturates.

|  | 1-channel pool | 2-channel pool |
| --- | --- | --- |
| Victim slowdown, + 1 STREAM | 1.04× | 1.003× |
| Victim p99.9, + 1 STREAM (alone 505 ns) | 955 ns | 510 ns |
| **Victim slowdown, + 3 STREAM** | **1.49×** | **1.02×** |
| Victim mean / p99 / p99.9, + 3 STREAM (alone 252.7 / 460 / 505 ns) | 385.7 / 1,015 / 1,410 ns | 257.7 / 460 / 540 ns |
| STREAM slowdown, + 3 STREAM | 1.22–1.48× | 0.98–1.06× |
| STREAM (2 threads) alone, bandwidth | 3.1–3.85 GB/s | 4.5–5.2 GB/s |
| Controller queue, STREAM alone (avg) | 10.1 | 2.9 |
| Controller read latency, 3 STREAM + victim | 358 ns | 55 ns |
| Cycles with the DRAM queue full, 3 STREAM + victim | 393 million | 3,480 |

With twice the channels and banks, a 2-thread STREAM host runs about 35% faster and leaves almost no queue for the victim to land in. Three such hosts push about 13.5–15 GB/s into the 2-channel pool, which is well below its saturation point.

**More traffic, less queueing than an earlier 4-host run.** The earlier 4 single-thread STREAM hosts on the same 2-channel pool sent about 10.4 GB/s, yet each request waited 75 ns in the controller and the DRAM queue was full for 265,559 cycles. The 3 two-thread hosts send more but wait 55 ns, with the queue full for only 3,480 cycles. The leading explanation is that 4 separate hosts keep 4 different rows competing in every bank, against 3 here; this was not checked.

**The Add/Triad variation shows here too.** Next to the victim alone, STREAM's Add ran 5.1% faster and Triad 2.6% slower on 2 channels, the reverse of the 1-channel run. Copy and Scale moved under 0.7%.

## Repeatability: three independent runs

The victim's slowdown holds across three independent runs on the 1-channel pool: **1.49 ± 0.04** (range 1.46–1.53). Adding the victim does not measurably change STREAM.

The simulator is deterministic, so restoring the same checkpoint gives the same numbers. Each run therefore boots every host again under KVM and takes a new checkpoint, so the hosts start from different states. Each run has four experiments: STREAM alone, victim alone, 3 STREAM hosts, and 3 STREAM hosts with the victim. STREAM uses 2 threads, as in the rest of this report. Run 1 is the run reported in the sections above.

**Alone baselines.** STREAM alone varies from run to run by itself, while the victim alone barely changes.

| Alone | Run 1 | Run 2 | Run 3 | Mean |
| --- | --- | --- | --- | --- |
| STREAM Copy (ms) | 52.15 | 50.84 | 51.54 | 51.51 |
| STREAM Scale (ms) | 52.50 | 52.26 | 52.19 | 52.31 |
| STREAM Add (ms) | 87.21 | 81.77 | 84.43 | 84.47 |
| STREAM Triad (ms) | 83.62 | 76.84 | 86.16 | 82.21 |
| Victim (ns per pool read) | 273.7 | 273.4 | 273.6 | 273.6 |

Below, every slowdown is measured against the mean of the three alone runs, so run 1's values differ slightly from the tables above, which used run 1's alone run.

**Victim next to 3 STREAM hosts.** Alone, the victim's mean latency is 246 ns, p50 250 ns, p99 460 ns and p99.9 505 ns in every run.

| Run | Slowdown | Mean latency (ns) | p50 (ns) | p99 (ns) | p99.9 (ns) |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.486 | 379 | 345 | 1010 | 1410 |
| 2 | 1.533 | 391 | 355 | 1080 | 1515 |
| 3 | 1.462 | 372 | 340 | 990 | 1370 |
| Mean | 1.494 ± 0.036 | 381 | 347 | 1027 | 1432 |

**STREAM slowdown.** Each run's value is the mean of its 3 STREAM hosts; the range covers all 9 host values.

| Kernel | 3 STREAM: runs 1 / 2 / 3 | 3 STREAM: mean (range) | + victim: runs 1 / 2 / 3 | + victim: mean (range) |
| --- | --- | --- | --- | --- |
| Copy | 1.28 / 1.40 / 1.43 | 1.37 (1.27–1.44) | 1.50 / 1.50 / 1.37 | 1.45 (1.36–1.50) |
| Scale | 1.36 / 1.32 / 1.33 | 1.34 (1.31–1.37) | 1.35 / 1.33 / 1.38 | 1.35 (1.32–1.39) |
| Add | 1.28 / 1.30 / 1.37 | 1.32 (1.27–1.37) | 1.29 / 1.33 / 1.23 | 1.28 (1.23–1.35) |
| Triad | 1.34 / 1.25 / 1.19 | 1.26 (1.19–1.34) | 1.24 / 1.26 / 1.23 | 1.24 (1.23–1.26) |

**Pool controller.** The pool is saturated to the same degree in all six contention runs.

| Run | 3 STREAM: read latency, queue avg / max, queue-full cycles | + victim: read latency, queue avg / max, queue-full cycles |
| --- | --- | --- |
| 1 | 356 ns, 41.1 / 116, 382 M | 358 ns, 42.2 / 134, 393 M |
| 2 | 354 ns, 41.2 / 180, 378 M | 366 ns, 42.6 / 158, 395 M |
| 3 | 362 ns, 41.5 / 129, 383 M | 340 ns, 41.0 / 98, 377 M |

**What the repeats show.**

- **The victim's slowdown is robust.** It is 1.46–1.53× in every run, and its p99 more than doubles each time (460 ns → 990–1080 ns).
- **FCFS hurts the latency-bound host most.** The victim moves only about 0.16 GB/s, yet it slows more than every STREAM kernel does on average (1.24–1.45×).
- **The victim does not measurably change STREAM.** The differences go both ways (Copy +0.08, Scale +0.01, Add −0.04, Triad −0.02) and lie within the spread between runs. The victim adds about 0.8 M reads to STREAM's 31.5 M, and the pool statistics are the same with or without it.
- **The spread is between runs, not between hosts.** Within a run the 3 STREAM hosts stay within 2.1% of each other. Between runs, Copy varies the most (up to about 15%) and Scale the least (about 5%).
- **Single-run STREAM slowdowns need care.** Even STREAM alone varies by up to 12% between runs (Triad 76.8–86.2 ms), so both the alone baseline and the contention runs should be averaged.

## Limitations

- **Queueing and row misses are not separated.** The victim's extra 133 ns per load combines waiting in the queue with longer DRAM service caused by row conflicts. The pool controller's statistics combine all hosts, so per-host queue wait, service time and row hits were not measured at this stage; the scheduler front end of doc 12 adds per-host counters.
- **Row-hit rates were not measured,** so the explanation for saturating at about 8 GB/s (row misses plus FIFO bank queues) is likely but was not confirmed here.
- **The DRAM model has no row-hit reordering.** Real controllers use FR-FCFS and reach a higher share of peak, so absolute saturation points will differ on real hardware. The comparison between hosts under the same model is what matters for fairness.
- **Simulator artefacts at the bridge.** About 2–3% of the victim's reads return in under 100 ns, and the main latency peak sits about 10 ns below the link delay. Both are excluded or constant across runs; the root cause was not found.
- **Host model.** The measured region uses a blocking timing CPU, so a host's requests in flight come mostly from its prefetchers. Two cores per host stand in for a real server's dozens of cores.
- **Repeats cover the 1-channel pool only.** The 1-channel experiments have three independent runs each. The 2-channel and 1 STREAM + victim results are single runs, so differences of a few percent there are within run-to-run variation.
- **Why the 2-channel pool queues less with 3 two-thread hosts than it did with 4 single-thread hosts was not confirmed** (fewer hosts competing for rows in each bank is the leading explanation).
