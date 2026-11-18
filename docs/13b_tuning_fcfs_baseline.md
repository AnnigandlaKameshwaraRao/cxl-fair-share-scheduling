# Scheduler Tuning Results: FCFS Baseline

Measured against each workload running alone under FCFS, ATLAS has the lowest mean largest slowdown (1.79 with the 1M quantum), and SAA with smoothing is fifth (1.91). Unfairness is a near tie between ATLAS 1M (1.45 to 1.46) and SAA with smoothing (1.46). The same 27 runs measured against FR-FCFS alone runs put SAA with smoothing first; the difference is how the two baselines treat row-hit gains.

## Metrics

Every metric is computed per mix from its four hosts. A "mean" column is the average of the three mixes' values (m04, m13, m01), not a metric of averaged slowdowns. Values come from unrounded slowdowns, so they can differ by 0.01 from the rounded numbers in the tables.

| Metric | What it shows | How it is calculated | Better |
| --- | --- | --- | --- |
| Progress | How fast a host runs | Instructions per simulated second; pool requests per second for MERCI and multichase, whose instruction counts include spin and wait loops | Higher |
| Slowdown | How much sharing slows one host | Progress alone under FCFS ÷ progress in the mix | Lower; 1 = not slowed |
| Largest slowdown | The worst-treated host | Largest of the four slowdowns | Lower |
| Mean slowdown | The average host | Mean of the four slowdowns | Lower |
| Unfairness | Gap between the worst- and best-treated host | Largest slowdown ÷ smallest; ATLAS 1M in m13 slows its hosts 1.80, 1.90, 1.63 and 1.35 times, so 1.90 ÷ 1.35 = 1.41 | Lower; 1 = all slowed equally |
| Spread (CV) | How far all four slowdowns scatter, not just the two ends | Standard deviation ÷ mean of the four slowdowns | Lower; 0 = all equal |
| Jain, progress | Evenness of progress | (x1 + x2 + x3 + x4)² ÷ (4 × (x1² + x2² + x3² + x4²)), with x = 1 ÷ slowdown | Higher; 1 = equal, 0.25 = one host gets everything |
| Jain, bandwidth share | Evenness of each host's pool bandwidth relative to what it gets alone | Same formula, with x = pool bandwidth in the mix ÷ pool bandwidth alone | Higher |
| Bandwidth-share unfairness | Gap in bandwidth share | Largest bandwidth share ÷ smallest | Lower |
| Jain, raw bandwidth | Evenness of the GB/s each host gets, ignoring demand | Same formula, with x = pool bandwidth in the mix (GB/s) | Higher, but equal GB/s is not the goal when demands differ |
| Weighted speedup | System throughput | Sum of 1 ÷ slowdown over the four hosts | Higher; 4 = no loss |
| Harmonic speedup | Throughput that weighs a badly slowed host heavily | 4 ÷ sum of the four slowdowns | Higher; 1 = no loss |
| Delivered bandwidth | What the pool delivers | Sum of the four hosts' pool bandwidth in the mix | Higher; 19.2 GB/s peak |

A slowdown below 1 would mean a host ran faster in the mix than alone; the lowest here is tealeaf under FR-FCFS in m04, at 1.00.

## Summary over the three mixes

Means over mixes m04, m13 and m01, every scheduler against the same FCFS alone runs. The Metrics section above says what each column is and which direction is better; the best value in each column is in bold.

| Scheduler | Mean largest slowdown | Mean unfairness | Mean weighted speedup | Mean slowdown | Mean spread (CV) | Mean Jain, progress | Mean Jain, bandwidth share | Mean bandwidth-share unfairness | Mean Jain, raw bandwidth | Mean harmonic speedup | Mean delivered (GB/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATLAS 1M | **1.79** | 1.46 | 2.63 | 1.56 | **0.14** | 0.975 | 0.981 | 1.42 | 0.901 | 0.643 | **16.7** |
| ATLAS 1M + rule | 1.80 | **1.45** | 2.63 | 1.56 | **0.14** | **0.976** | **0.983** | **1.40** | 0.900 | 0.644 | 16.6 |
| ATLAS 10M + rule | 1.82 | 1.51 | 2.65 | 1.56 | 0.15 | 0.971 | 0.976 | 1.50 | **0.903** | 0.645 | **16.7** |
| ATLAS 10M | 1.84 | 1.52 | **2.66** | **1.55** | 0.16 | 0.971 | 0.977 | 1.49 | **0.903** | **0.647** | **16.7** |
| SAA, smoothing 0.75 | 1.91 | 1.46 | 2.49 | 1.65 | **0.14** | **0.976** | 0.967 | 1.63 | 0.853 | 0.608 | 16.3 |
| SAA | 2.03 | 1.65 | 2.52 | 1.65 | 0.18 | 0.964 | 0.956 | 1.78 | 0.848 | 0.608 | 16.3 |
| TCM | 2.07 | 1.64 | 2.63 | 1.59 | 0.20 | 0.965 | 0.974 | 1.46 | 0.877 | 0.632 | 16.5 |
| BLISS | 2.18 | 1.95 | 2.57 | 1.67 | 0.24 | 0.933 | 0.929 | 2.16 | 0.815 | 0.603 | 16.6 |
| PAR-BS | 2.20 | 1.70 | 2.39 | 1.76 | 0.21 | 0.952 | 0.941 | 2.01 | 0.812 | 0.571 | 16.2 |
| FR-FCFS | 3.00 | 2.81 | 2.38 | 1.94 | 0.36 | 0.879 | 0.870 | 3.30 | 0.788 | 0.519 | 16.6 |
| FCFS | 4.90 | 2.83 | 1.46 | 3.20 | 0.37 | 0.866 | 0.882 | 2.94 | 0.758 | 0.315 | 10.6 |

The FCFS row is identical to doc 13, since FCFS was already measured against FCFS alone runs there.

- **Mean slowdown** is lowest for ATLAS 10M (1.55); SAA is at 1.65 and FR-FCFS at 1.94.
- **Jain's index on progress** compresses the differences: every fairness scheduler scores 0.93 to 0.976 and FR-FCFS 0.879, though FR-FCFS's largest slowdown (3.00) is 1.7 times ATLAS 1M's (1.79). ATLAS 1M with the rule and SAA with smoothing tie at 0.976.
- **Bandwidth share** is most even under ATLAS 1M with the rule (Jain 0.983, unfairness 1.40). SAA evens progress more than bandwidth share: in m13 its Jain index is 0.986 on progress and 0.950 on bandwidth share. BLISS and PAR-BS leave the most uneven bandwidth shares of the fairness schedulers (2.16 and 2.01).
- **Harmonic speedup** is highest for ATLAS 10M (0.647); SAA is at 0.608 and FR-FCFS at 0.519.
- **Delivered bandwidth** stays between 16.2 and 16.7 GB/s for every scheduler that keeps FR-FCFS's row-hit order, from 2.3% below to 0.7% above FR-FCFS's 16.6 GB/s; FCFS delivers 10.6 GB/s.

## Largest slowdown per mix

An ATLAS variant has the lowest largest slowdown in every mix: 10M in m04 (1.89), 1M in m13 (1.90, tied with SAA with smoothing) and 1M in m01 (1.55).

## Why the ranking changes

Every slowdown in this doc is computed directly: the host's progress alone under FCFS ÷ its progress in the mix. The mix runs are the same as in doc 13; only the alone run changes. FCFS alone runs are slower than FR-FCFS alone runs, because they get no row hits, and the streaming hosts lose the most. The table below shows that gap. It explains the shift and is not used in any calculation: since the mix run is the same, a host's FCFS-baseline slowdown equals its FR-FCFS-baseline slowdown divided by this ratio (tealeaf under ATLAS 10M in m04: 3.06 ÷ 1.98 = 1.55, the value computed directly).

| Host (mix slot) | Alone progress under FR-FCFS ÷ alone progress under FCFS | Row-hit rate alone, FR-FCFS |
| --- | --- | --- |
| tealeaf (slot 0) | 1.98 | 0.74 |
| STREAM (slot 1) | 1.69 | 0.78 |
| fotonik3d (slot 1) | 1.32 | 0.74 |
| fotonik3d (slot 2) | 1.28 | 0.74 |
| roms (slot 2) | 1.24 | 0.81 |
| MERCI (slot 3) | 1.19 | 0.82 |
| streamcluster (slot 3) | 1.05 | 0.91 |
| multichase (slot 3) | 1.03 | 0.94 |

ATLAS's largest slowdowns fall on tealeaf and STREAM, the two hosts with the biggest row-hit gains: for ATLAS 10M, tealeaf 3.06 in m04 and STREAM 3.45 in m13 against FR-FCFS alone runs. Dividing by 1.98 and 1.69 moves ATLAS ahead of SAA. SAA's slowdowns are spread more evenly across hosts, including the victims, so less of them is discounted. The FR-FCFS baseline counts a lost row hit as slowdown; the FCFS baseline counts the row hits a scheduler keeps as a gain.

## Tuning choices under this baseline

The ATLAS variants stay within 3% of each other on mean largest slowdown (1.79 to 1.84); here the 1M quantum is narrowly ahead, where the FR-FCFS baseline put 10M with the rule narrowly ahead. Smoothing lowers SAA's largest slowdown in every mix.

| Variant | Largest m04 | Largest m13 | Largest m01 | Mean largest | Mean unfairness | Mean weighted speedup |
| --- | --- | --- | --- | --- | --- | --- |
| ATLAS 10M | 1.89 | 2.04 | 1.60 | 1.84 | 1.52 | 2.66 |
| ATLAS 10M + rule | 1.89 | 1.97 | 1.61 | 1.82 | 1.51 | 2.65 |
| ATLAS 1M | 1.91 | 1.90 | 1.55 | 1.79 | 1.46 | 2.63 |
| ATLAS 1M + rule | 1.91 | 1.90 | 1.58 | 1.80 | 1.45 | 2.63 |
| SAA | 2.33 | 1.96 | 1.79 | 2.03 | 1.65 | 2.52 |
| SAA, smoothing 0.75 | 2.17 | 1.90 | 1.67 | 1.91 | 1.46 | 2.49 |

Smoothing lowers SAA's largest slowdown in all three mixes (by 7% on m04 and m01, 3% on m13) and its unfairness from 1.65 to 1.46, for 1% less weighted speedup.

## Results per mix

Each host's slowdown against its own FCFS alone run. Host 3 is the victim in m04 and m01 and the lightest host in m13. The columns after the four hosts are the per-mix metrics defined in the Metrics section.

### m04: tealeaf, fotonik3d, roms, MERCI

| Scheduler | tealeaf | fotonik3d | roms | MERCI | Unfairness | Weighted speedup | Mean slowdown | Spread (CV) | Jain, progress | Jain, bandwidth share | Bandwidth-share unfairness | Jain, raw bandwidth | Harmonic speedup | Delivered (GB/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.39 | 1.90 | 3.81 | 6.45 | 3.39 | 1.36 | 3.64 | 0.49 | 0.851 | 0.863 | 3.39 | 0.785 | 0.275 | 10.6 |
| FR-FCFS | 1.00 | 1.80 | 2.32 | 3.65 | 3.66 | 2.26 | 2.19 | 0.44 | 0.813 | 0.826 | 3.69 | 0.778 | 0.456 | 16.5 |
| ATLAS 10M | 1.55 | 1.88 | 1.89 | 1.11 | 1.71 | 2.61 | 1.61 | 0.20 | 0.948 | 0.953 | 1.81 | 0.955 | 0.622 | 16.5 |
| ATLAS 10M + rule | 1.55 | 1.88 | 1.89 | 1.11 | 1.70 | 2.61 | 1.61 | 0.20 | 0.949 | 0.954 | 1.81 | 0.955 | 0.622 | 16.5 |
| ATLAS 1M | 1.57 | 1.86 | 1.91 | 1.15 | 1.67 | 2.57 | 1.62 | 0.19 | 0.955 | 0.962 | 1.65 | 0.953 | 0.617 | 16.5 |
| ATLAS 1M + rule | 1.52 | 1.86 | 1.91 | 1.17 | 1.64 | 2.57 | 1.62 | 0.18 | 0.959 | 0.965 | 1.62 | 0.951 | 0.619 | 16.5 |
| TCM | 1.32 | 1.81 | 2.27 | 1.24 | 1.84 | 2.56 | 1.66 | 0.25 | 0.948 | 0.958 | 1.63 | 0.932 | 0.602 | 16.4 |
| BLISS | 1.05 | 1.80 | 2.44 | 2.03 | 2.33 | 2.41 | 1.83 | 0.28 | 0.893 | 0.915 | 1.95 | 0.840 | 0.546 | 16.5 |
| PAR-BS | 1.17 | 1.74 | 2.10 | 2.27 | 1.94 | 2.35 | 1.82 | 0.23 | 0.928 | 0.938 | 1.94 | 0.851 | 0.550 | 16.4 |
| SAA | 1.18 | 1.85 | 2.33 | 1.55 | 1.98 | 2.46 | 1.73 | 0.24 | 0.941 | 0.954 | 1.73 | 0.890 | 0.579 | 16.2 |
| SAA, smoothing | 1.24 | 1.84 | 2.17 | 1.63 | 1.76 | 2.43 | 1.72 | 0.20 | 0.957 | 0.965 | 1.57 | 0.893 | 0.582 | 16.2 |

### m13: tealeaf, STREAM, fotonik3d, streamcluster

| Scheduler | tealeaf | STREAM | fotonik3d | streamcluster | Unfairness | Weighted speedup | Mean slowdown | Spread (CV) | Jain, progress | Jain, bandwidth share | Bandwidth-share unfairness | Jain, raw bandwidth | Harmonic speedup | Delivered (GB/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.93 | 3.83 | 1.63 | 3.16 | 2.35 | 1.53 | 2.89 | 0.28 | 0.888 | 0.876 | 3.02 | 0.791 | 0.346 | 10.7 |
| FR-FCFS | 1.20 | 2.00 | 1.52 | 2.36 | 1.97 | 2.42 | 1.77 | 0.25 | 0.936 | 0.877 | 3.50 | 0.842 | 0.566 | 16.8 |
| ATLAS 10M | 1.62 | 2.04 | 1.64 | 1.30 | 1.57 | 2.48 | 1.65 | 0.16 | 0.975 | 0.988 | 1.32 | 0.988 | 0.606 | 17.0 |
| ATLAS 10M + rule | 1.63 | 1.97 | 1.73 | 1.30 | 1.52 | 2.47 | 1.66 | 0.15 | 0.976 | 0.987 | 1.36 | 0.990 | 0.604 | 17.1 |
| ATLAS 1M | 1.80 | 1.90 | 1.63 | 1.35 | 1.41 | 2.44 | 1.67 | 0.13 | 0.982 | 0.994 | 1.25 | 0.985 | 0.598 | 16.9 |
| ATLAS 1M + rule | 1.78 | 1.90 | 1.63 | 1.36 | 1.40 | 2.44 | 1.67 | 0.12 | 0.983 | 0.994 | 1.24 | 0.984 | 0.600 | 16.9 |
| TCM | 1.59 | 2.08 | 1.52 | 1.59 | 1.36 | 2.40 | 1.69 | 0.13 | 0.987 | 0.989 | 1.34 | 0.942 | 0.590 | 16.8 |
| BLISS | 1.23 | 2.06 | 1.52 | 2.18 | 1.77 | 2.42 | 1.75 | 0.22 | 0.947 | 0.892 | 3.08 | 0.853 | 0.573 | 16.7 |
| PAR-BS | 1.45 | 2.23 | 1.46 | 2.16 | 1.53 | 2.29 | 1.82 | 0.20 | 0.960 | 0.905 | 2.68 | 0.844 | 0.548 | 16.3 |
| SAA | 1.41 | 1.88 | 1.57 | 1.96 | 1.39 | 2.39 | 1.71 | 0.13 | 0.982 | 0.938 | 2.17 | 0.896 | 0.586 | 16.4 |
| SAA, smoothing | 1.46 | 1.90 | 1.56 | 1.90 | 1.31 | 2.38 | 1.70 | 0.12 | 0.986 | 0.950 | 1.98 | 0.905 | 0.587 | 16.5 |

### m01: tealeaf, STREAM, fotonik3d, multichase

| Scheduler | tealeaf | STREAM | fotonik3d | multichase | Unfairness | Weighted speedup | Mean slowdown | Spread (CV) | Jain, progress | Jain, bandwidth share | Bandwidth-share unfairness | Jain, raw bandwidth | Harmonic speedup | Delivered (GB/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FCFS | 2.73 | 3.53 | 1.61 | 4.42 | 2.75 | 1.50 | 3.07 | 0.34 | 0.860 | 0.908 | 2.42 | 0.697 | 0.325 | 10.4 |
| FR-FCFS | 1.07 | 1.90 | 1.50 | 2.98 | 2.79 | 2.46 | 1.86 | 0.38 | 0.888 | 0.905 | 2.72 | 0.744 | 0.537 | 16.6 |
| ATLAS 10M | 1.24 | 1.60 | 1.52 | 1.25 | 1.28 | 2.89 | 1.40 | 0.11 | 0.988 | 0.989 | 1.33 | 0.765 | 0.712 | 16.6 |
| ATLAS 10M + rule | 1.23 | 1.61 | 1.52 | 1.27 | 1.31 | 2.88 | 1.41 | 0.12 | 0.987 | 0.989 | 1.34 | 0.765 | 0.711 | 16.6 |
| ATLAS 1M | 1.33 | 1.55 | 1.52 | 1.19 | 1.31 | 2.90 | 1.40 | 0.11 | 0.988 | 0.988 | 1.37 | 0.766 | 0.715 | 16.6 |
| ATLAS 1M + rule | 1.31 | 1.58 | 1.52 | 1.20 | 1.32 | 2.89 | 1.40 | 0.11 | 0.987 | 0.989 | 1.35 | 0.766 | 0.714 | 16.5 |
| TCM | 1.10 | 1.87 | 1.52 | 1.20 | 1.71 | 2.94 | 1.42 | 0.21 | 0.961 | 0.976 | 1.42 | 0.756 | 0.703 | 16.5 |
| BLISS | 1.10 | 1.93 | 1.50 | 1.25 | 1.75 | 2.89 | 1.45 | 0.22 | 0.961 | 0.978 | 1.44 | 0.753 | 0.691 | 16.5 |
| PAR-BS | 1.29 | 2.10 | 1.43 | 1.70 | 1.63 | 2.54 | 1.63 | 0.19 | 0.969 | 0.981 | 1.41 | 0.741 | 0.614 | 16.0 |
| SAA | 1.14 | 1.79 | 1.53 | 1.60 | 1.58 | 2.72 | 1.51 | 0.16 | 0.969 | 0.977 | 1.45 | 0.757 | 0.660 | 16.2 |
| SAA, smoothing | 1.25 | 1.67 | 1.52 | 1.65 | 1.33 | 2.66 | 1.52 | 0.11 | 0.986 | 0.985 | 1.33 | 0.762 | 0.656 | 16.3 |

## Setup and measures

The runs are the same as in doc 13: 27 one-channel tuning runs (nine scheduler variants on three mixes) plus the FCFS and FR-FCFS O3 mixed runs. Only the alone runs they are measured against differ.

- **Pool.** One DDR4-2400-like channel, 19.2 GB/s peak, 2 ranks × 16 banks, 8 KiB rows, open page, fixed 250 ns link; 4 hosts of 4 O3 cores at 3 GHz; 100 ms windows.
- **Baseline.** The one-channel O3 alone run of the same workload and checkpoint slot under FCFS (SST's stock backend: FIFO bank queues, closed pages), for every scheduler.
