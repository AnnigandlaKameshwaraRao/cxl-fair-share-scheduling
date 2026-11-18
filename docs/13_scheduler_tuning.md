# Scheduler Tuning Results

Over the three tuning mixes, SAA with smoothing has the lowest mean largest slowdown (2.91) and the lowest mean unfairness (1.56). The four ATLAS variants lie within 2% of each other, and 10M with the over-threshold rule is narrowly best (3.04). Every scheduler cuts host 3's slowdown (MERCI, streamcluster, multichase) well below FR-FCFS's, but in m13 only SAA and ATLAS 10M with the rule bring the largest slowdown below FR-FCFS's 3.37.

## Summary over the three mixes

Means over mixes m04, m13 and m01. Largest slowdown and unfairness: lower is better. Weighted speedup: higher is better (4 = no loss).

| Scheduler | Mean largest slowdown | Mean unfairness | Mean weighted speedup |
| --- | --- | --- | --- |
| SAA, smoothing 0.75 | **2.91** | **1.56** | 1.74 |
| SAA | 3.03 | 1.66 | 1.76 |
| ATLAS 10M + rule | 3.04 | 2.28 | 1.92 |
| ATLAS 10M | 3.07 | 2.31 | **1.93** |
| ATLAS 1M + rule | 3.07 | 2.27 | 1.92 |
| ATLAS 1M | 3.10 | 2.31 | 1.92 |
| TCM | 3.16 | 2.20 | 1.89 |
| BLISS | 3.26 | 1.93 | 1.79 |
| PAR-BS | 3.33 | 1.74 | 1.67 |
| FR-FCFS | 3.64 | 1.87 | 1.59 |
| FCFS | 4.90 | 2.83 | 1.46 |

Weighted speedup counts MERCI and multichase by pool request rate, like slowdown, so their spin and wait loops do not inflate it.

## Largest slowdown per mix

No scheduler has the lowest largest slowdown in every mix: PAR-BS leads m04 (2.69), SAA m13 (3.18) and ATLAS 1M m01 (2.62). SAA with smoothing is the only one within 0.2 of the best in all three.

## ATLAS: quantum and over-threshold rule

The four variants' largest slowdowns differ by at most 8% in any mix (m13: 3.32 to 3.57) and by 2% on the mean. 10M with the rule has the lowest mean (3.04). Weighted speedup is within 1% across the four (1.92 to 1.93).

| ATLAS variant | Largest m04 | Largest m13 | Largest m01 | Mean largest | Mean unfairness | Mean weighted speedup |
| --- | --- | --- | --- | --- | --- | --- |
| 10M | 3.06 | 3.45 | 2.69 | 3.07 | 2.31 | 1.93 |
| 10M + rule | 3.07 | 3.32 | 2.72 | 3.04 | 2.28 | 1.92 |
| 1M | 3.10 | 3.57 | 2.62 | 3.10 | 2.31 | 1.92 |
| 1M + rule | 3.01 | 3.52 | 2.67 | 3.07 | 2.27 | 1.92 |

The rule serves a request first once it has waited over 100,000 pool cycles since reaching the device, at admission and at the bank. It fires tens of thousands of times per run, almost entirely for the aggressors. With the 10M quantum it never fires for MERCI, streamcluster or multichase.

| Run | Host 0 | Host 1 | Host 2 | Host 3 |
| --- | --- | --- | --- | --- |
| m04, 10M + rule | tealeaf 23,191 | fotonik3d 27,409 | roms 3,356 | MERCI 0 |
| m04, 1M + rule | tealeaf 25,739 | fotonik3d 25,268 | roms 5,177 | MERCI 812 |
| m13, 10M + rule | tealeaf 28,736 | STREAM 15,883 | fotonik3d 74,520 | streamcluster 0 |
| m13, 1M + rule | tealeaf 34,109 | STREAM 21,959 | fotonik3d 54,526 | streamcluster 919 |
| m01, 10M + rule | tealeaf 19,408 | STREAM 2,719 | fotonik3d 49,293 | multichase 0 |
| m01, 1M + rule | tealeaf 21,906 | STREAM 13,602 | fotonik3d 37,592 | multichase 0 |

Requests admitted by the rule over the 100 ms run, per host.

## SAA: smoothing

Smoothing lowers SAA's largest slowdown by 7% in m04 and m01 and leaves m13 within 1%. Weighted speedup changes by under 2%. Both runs use the bandwidth estimate; smoothing weights the previous 10 µs epoch's estimate by 0.75 when ranking hosts.

| Mix | Largest: SAA | Largest: smoothing | Unfairness: SAA | Unfairness: smoothing | Weighted speedup: SAA | Weighted speedup: smoothing | Host 3: SAA | Host 3: smoothing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| m04 (victim MERCI) | 2.90 | **2.70** | 1.57 | **1.40** | 1.72 | 1.71 | 1.84 | 1.93 |
| m13 (host 3 streamcluster) | **3.18** | 3.21 | **1.58** | 1.61 | 1.66 | 1.66 | 2.06 | 2.00 |
| m01 (victim multichase) | 3.02 | **2.81** | 1.83 | **1.66** | 1.89 | 1.86 | 1.65 | 1.69 |

SAA spreads the slowdown more evenly than ATLAS but protects the single victim less: MERCI is at 1.93 under SAA with smoothing and 1.32 under ATLAS 10M, while tealeaf is at 2.45 and 3.06.

## Results per mix

Each host's slowdown against its own alone run. Host 3 is the victim in m04 and m01 and the lightest host in m13. The largest slowdown in each row is the one the chart above shows.

### m04: tealeaf, fotonik3d, roms, MERCI

| Scheduler | tealeaf | fotonik3d | roms | MERCI | Unfairness | Weighted speedup |
| --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.39 | 1.90 | 3.81 | 6.45 | 3.39 | 1.36 |
| FR-FCFS | 1.98 | 2.38 | 2.89 | 4.33 | 2.19 | 1.50 |
| ATLAS 10M | 3.06 | 2.49 | 2.35 | 1.32 | 2.32 | 1.91 |
| ATLAS 10M + rule | 3.07 | 2.49 | 2.35 | 1.32 | 2.33 | 1.91 |
| ATLAS 1M | 3.10 | 2.46 | 2.38 | 1.36 | 2.27 | 1.88 |
| ATLAS 1M + rule | 3.01 | 2.46 | 2.38 | 1.39 | 2.17 | 1.88 |
| TCM | 2.61 | 2.40 | 2.83 | 1.47 | 1.92 | 1.83 |
| BLISS | 2.08 | 2.39 | 3.04 | 2.41 | 1.46 | 1.64 |
| PAR-BS | 2.31 | 2.31 | 2.61 | 2.69 | 1.17 | 1.62 |
| SAA | 2.33 | 2.45 | 2.90 | 1.84 | 1.57 | 1.72 |
| SAA, smoothing | 2.45 | 2.44 | 2.70 | 1.93 | 1.40 | 1.71 |

### m13: tealeaf, STREAM, fotonik3d, streamcluster

| Scheduler | tealeaf | STREAM | fotonik3d | streamcluster | Unfairness | Weighted speedup |
| --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.93 | 3.83 | 1.63 | 3.16 | 2.35 | 1.53 |
| FR-FCFS | 2.37 | 3.37 | 1.94 | 2.49 | 1.74 | 1.64 |
| ATLAS 10M | 3.20 | 3.45 | 2.10 | 1.37 | 2.51 | 1.81 |
| ATLAS 10M + rule | 3.23 | 3.32 | 2.21 | 1.36 | 2.44 | 1.80 |
| ATLAS 1M | 3.57 | 3.21 | 2.09 | 1.42 | 2.52 | 1.78 |
| ATLAS 1M + rule | 3.52 | 3.21 | 2.08 | 1.43 | 2.47 | 1.78 |
| TCM | 3.14 | 3.50 | 1.95 | 1.67 | 2.10 | 1.72 |
| BLISS | 2.43 | 3.48 | 1.94 | 2.29 | 1.80 | 1.65 |
| PAR-BS | 2.88 | 3.76 | 1.86 | 2.27 | 2.03 | 1.59 |
| SAA | 2.79 | 3.18 | 2.01 | 2.06 | 1.58 | 1.66 |
| SAA, smoothing | 2.88 | 3.21 | 2.00 | 2.00 | 1.61 | 1.66 |

### m01: tealeaf, STREAM, fotonik3d, multichase

| Scheduler | tealeaf | STREAM | fotonik3d | multichase | Unfairness | Weighted speedup |
| --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.73 | 3.53 | 1.61 | 4.42 | 2.75 | 1.50 |
| FR-FCFS | 2.11 | 3.21 | 1.92 | 3.06 | 1.67 | 1.63 |
| ATLAS 10M | 2.46 | 2.69 | 1.95 | 1.29 | 2.09 | 2.07 |
| ATLAS 10M + rule | 2.43 | 2.72 | 1.95 | 1.30 | 2.09 | 2.06 |
| ATLAS 1M | 2.62 | 2.62 | 1.95 | 1.22 | 2.15 | 2.10 |
| ATLAS 1M + rule | 2.59 | 2.67 | 1.94 | 1.23 | 2.17 | 2.09 |
| TCM | 2.17 | 3.16 | 1.93 | 1.23 | 2.57 | 2.11 |
| BLISS | 2.18 | 3.26 | 1.92 | 1.29 | 2.53 | 2.06 |
| PAR-BS | 2.55 | 3.55 | 1.82 | 1.75 | 2.03 | 1.80 |
| SAA | 2.25 | 3.02 | 1.96 | 1.65 | 1.83 | 1.89 |
| SAA, smoothing | 2.48 | 2.81 | 1.95 | 1.69 | 1.66 | 1.86 |

## Setup and measures

The tuning set is 27 full-length runs: nine scheduler variants on three mixes. FCFS and FR-FCFS come from the O3 mixed runs on the same one-channel pool.

- **Hosts.** 4 hosts, each with 4 x86 cores at 3 GHz on gem5's O3 CPU; L1 32 KiB, L2 512 KiB, L3 8 MiB.
- **Pool.** One DDR4-2400-like channel in SST, 19.2 GB/s peak, 2 ranks × 16 banks, 8 KiB rows, open page, behind a fixed 250 ns link. Host i uses pool slot i and restores that workload's slot-i checkpoint.
- **Schedulers.** All run in the pool controller. Requests wait in per-host queues and are admitted into each channel's 32 pending slots; a bank then picks by host rank, then row hit, then age. The scheduler sets the host ranks.
- **Window.** 100 ms of simulated time from restore, statistics every 10 ms.
- **Mixes.** m04 and m01 are three aggressors and one victim (MERCI, multichase). m13 is four aggressors, of which streamcluster is the lightest.
- **Variants.** ATLAS with a 10M or 1M cycle quantum, each with and without the over-threshold rule (100,000 cycles). SAA with the bandwidth estimate, with and without smoothing 0.75. TCM, BLISS and PAR-BS at one setting each.

Measures follow the O3 mixed runs exactly:

- **Slowdown** = alone progress ÷ mix progress. Progress is the instruction rate, or the pool request rate for MERCI and multichase, whose instruction counts include spin and wait loops.
- **Baseline.** The one-channel O3 alone run of the same workload and checkpoint slot under FR-FCFS, since every tuned scheduler orders bank requests by row hit and age beneath host rank. FCFS rows use FCFS alone runs.
- **Unfairness** = largest slowdown ÷ smallest in the mix.
- **Weighted speedup** = the sum of the four hosts' mix-to-alone progress ratios, the sum of 1 ÷ slowdown (4 = no loss). It uses the same progress measure as slowdown; the O3 mixed runs counted instructions for all four hosts, which flattered mixes with MERCI or multichase.
