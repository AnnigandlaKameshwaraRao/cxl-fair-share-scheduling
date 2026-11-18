# Campaign Alone Runs: The 2-Channel Front End

- With one host, the new per-channel front end leaves 2-channel FCFS and FR-FCFS almost unchanged: 59 of the 96 runs are bit-identical to the O3 2-channel runs, and no run's instruction rate moves by more than 3% (STREAM slot 2 under FCFS, −2.98%).
- PAR-BS is not FR-FCFS when a host runs alone. On one channel it slows tealeaf and STREAM by 11.5% each (instruction rate, mean of 4 slots) and cuts MERCI's pool bandwidth by 7.7%; the other 9 workloads stay within ±1.3%.
- On two channels PAR-BS costs less: STREAM −6.6% and tealeaf −1.1%, the rest within ±0.7% (MERCI by pool bandwidth, +0.3%).
- The cost comes from PAR-BS's batches: a row hit outside the current batch waits behind the batch's row misses, so tealeaf's row-hit rate falls from 0.74 to 0.63 and STREAM's from 0.78 to 0.67 on one channel.
- BLISS, ATLAS, TCM and SAA do act as FR-FCFS alone: on both channel counts each one's check run matches FR-FCFS in every gem5 statistic of all 10 dumps.
- FCFS does get row hits. The earlier alone report said its row-hit rate is 0 by design; the new 2-channel FCFS runs count 0.01 to 0.64 per run.
- All 192 runs (12 workloads, 4 checkpoint slots; PAR-BS on 1 channel; FCFS, FR-FCFS and PAR-BS on 2 channels) reached the end of their 100 ms window.

## Setup

Each run puts one workload on one host, with its data in the pool, from the same checkpoints as the O3 alone runs. Host, caches, guest, link, DRAM timing, 8 KiB rows and the 100 ms window are unchanged. Two things are new: a per-host front end inside the pool device, and PAR-BS.

| Part | Setting |
| --- | --- |
| Front end (new) | requests go straight to a per-host queue of their own channel; a channel arbiter admits them to that channel's 32 pending slots. One host: oldest first. |
| Before (O3 runs) | one front queue fed every channel and stopped at the first request a full channel refused |
| FCFS | the btpmem copy of SST's stock bank logic: FIFO bank queues, closed page. A check run of the copy and the stock code matches in every statistic. |
| FR-FCFS | oldest open-row hit first, else oldest; open page; no cap on row hits |
| PAR-BS | when no batch request is left, the up to 5 oldest requests per host in every bank form a batch. Batch requests first, then row hit, then host rank, then oldest. Open page. |
| BLISS, ATLAS, TCM, SAA | FR-FCFS bank queues with host priority before row hit; with one host every request has the same priority |

One row per part of the model that changed or is compared, with its setting as configured; nothing in it is calculated.

On one channel there is no second channel to block, so the O3 1-channel FCFS and FR-FCFS alone runs stay the baselines there. Every slowdown in the campaign's mixes is measured against the alone run on the same channel count and scheduler:

| Scheduler | Alone baseline, 1 channel | Alone baseline, 2 channels |
| --- | --- | --- |
| FCFS | O3 FCFS alone runs | new FCFS runs (48) |
| FR-FCFS | O3 FR-FCFS alone runs | new FR-FCFS runs (48) |
| BLISS, ATLAS, TCM, SAA | O3 FR-FCFS alone runs | new FR-FCFS runs |
| PAR-BS | new PAR-BS runs (48) | new PAR-BS runs (48) |

One row per scheduler; the new runs cover 12 workloads × 4 checkpoint slots each. The equivalence runs in "Same as FR-FCFS alone" are what let BLISS, ATLAS, TCM and SAA share the FR-FCFS baseline.

## Measures

The measures are those of the O3 alone report (doc 10), each in its own column for every set-up. A run's figure covers its statistics periods; a workload's figure is the mean of its 4 slots, and a change is the mean of the 4 per-slot changes.

| Measure | Unit | What it counts |
| --- | --- | --- |
| Pool bandwidth | GB/s | read and write requests the host sends to the pool × 64 B ÷ the covered time |
| Pool latency | ns | mean time from a request leaving the host to its reply, weighted by each period's request count, including the link's fixed 250 ns |
| Instruction rate | G instructions/s | instructions committed by the host's 4 cores ÷ the covered time |
| Row-hit rate | share of accesses | 1 − activates ÷ column commands, counted by the btpmem bank code |
| L3 prefetches | per 1000 instructions | prefetches issued by the host's shared L3 stride prefetcher |
| L3 demand misses | per 1000 instructions | demand accesses that miss in the L3 and wait for memory |

The covered time is the sum of a run's statistics periods, 90 to 111 ms; hnswlib, STREAM and LLM inference write statistics dumps of their own (12 to 40 per run instead of 10), whose periods overlap, so some of their runs exceed 100 ms. Row-hit rates exist for every new run, FCFS included, but not for the O3 1-channel FCFS runs, which used SST's stock code. The campaign's slowdowns use the instruction rate as progress, except pool bandwidth for MERCI and multichase.

## Results per workload

On one channel PAR-BS gives up most for the two workloads that load it hardest: tealeaf falls from 13.87 to 12.30 GB/s and its pool latency rises by 50 ns. On two channels PAR-BS stays within 0.22 GB/s of FR-FCFS for every workload (STREAM, 9.52 against 9.30). Values are means of the 4 slots; aggressors first, as in Phase 1.

### One channel

| Workload | Role | Bandwidth FR-FCFS (GB/s) | Bandwidth PAR-BS (GB/s) | Latency FR-FCFS (ns) | Latency PAR-BS (ns) | Instr. rate FR-FCFS (G/s) | Instr. rate PAR-BS (G/s) | Row-hit rate FR-FCFS | Row-hit rate PAR-BS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tealeaf | aggressor | 13.87 | 12.30 | 399 | 449 | 9.80 | 8.67 | 0.74 | 0.63 |
| STREAM | aggressor | 12.14 | 10.55 | 316 | 325 | 1.59 | 1.41 | 0.78 | 0.67 |
| fotonik3d | aggressor | 11.72 | 11.56 | 408 | 411 | 5.21 | 5.16 | 0.74 | 0.71 |
| streamcluster | aggressor | 5.50 | 5.50 | 285 | 286 | 4.89 | 4.89 | 0.91 | 0.90 |
| roms | aggressor | 10.02 | 9.84 | 320 | 324 | 10.96 | 10.82 | 0.79 | 0.77 |
| LLM inference | aggressor | 3.96 | 3.96 | 269 | 269 | 10.47 | 10.48 | 0.97 | 0.96 |
| MERCI | victim | 3.47 | 3.20 | 292 | 294 | 1.95 | 2.00 | 0.82 | 0.71 |
| graph500 | victim | 3.70 | 3.70 | 292 | 293 | 1.92 | 1.92 | 0.27 | 0.27 |
| hnswlib | victim | 0.54 | 0.54 | 278 | 278 | 2.48 | 2.48 | 0.76 | 0.74 |
| cactus | victim | 1.55 | 1.56 | 292 | 291 | 3.18 | 3.18 | 0.51 | 0.49 |
| multichase | victim | 0.22 | 0.22 | 264 | 263 | 0.041 | 0.041 | 0.95 | 0.95 |
| Marian | victim | 0.014 | 0.014 | 273 | 273 | 6.07 | 6.07 | 0.99 | 0.99 |

One row per workload on one channel; each value is the mean of its 4 slot runs. FR-FCFS: the O3 alone runs, which are also the baseline for BLISS, ATLAS, TCM and SAA. PAR-BS: the new runs. Measures as defined above. The O3 1-channel FCFS figures are unchanged and are in the O3 alone report (doc 10).

### Two channels

| Workload | Bandwidth FCFS (GB/s) | Bandwidth FR-FCFS (GB/s) | Bandwidth PAR-BS (GB/s) | Latency FCFS (ns) | Latency FR-FCFS (ns) | Latency PAR-BS (ns) | Instr. rate FCFS (G/s) | Instr. rate FR-FCFS (G/s) | Instr. rate PAR-BS (G/s) | Row-hit rate FR-FCFS | Row-hit rate PAR-BS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tealeaf | 13.21 | 14.22 | 14.01 | 337 | 308 | 313 | 9.43 | 10.04 | 9.93 | 0.47 | 0.44 |
| STREAM | 8.97 | 9.52 | 9.30 | 304 | 296 | 299 | 1.19 | 1.29 | 1.20 | 0.51 | 0.46 |
| fotonik3d | 11.63 | 12.18 | 12.17 | 300 | 289 | 289 | 5.23 | 5.48 | 5.48 | 0.61 | 0.60 |
| streamcluster | 4.39 | 4.82 | 4.83 | 282 | 274 | 274 | 4.35 | 4.53 | 4.53 | 0.85 | 0.85 |
| roms | 6.85 | 7.06 | 7.04 | 294 | 285 | 286 | 8.94 | 9.11 | 9.10 | 0.66 | 0.65 |
| LLM inference | 3.97 | 4.20 | 4.19 | 276 | 265 | 265 | 10.54 | 11.01 | 11.01 | 0.98 | 0.98 |
| MERCI | 2.71 | 2.89 | 2.90 | 289 | 285 | 287 | 1.23 | 1.44 | 1.23 | 0.55 | 0.53 |
| graph500 | 3.78 | 3.68 | 3.68 | 282 | 288 | 288 | 1.98 | 1.92 | 1.92 | 0.24 | 0.24 |
| hnswlib | 0.35 | 0.36 | 0.36 | 278 | 277 | 277 | 2.68 | 2.70 | 2.71 | 0.62 | 0.62 |
| cactus | 1.40 | 1.42 | 1.40 | 282 | 279 | 280 | 3.14 | 3.14 | 3.13 | 0.51 | 0.49 |
| multichase | 0.22 | 0.22 | 0.22 | 272 | 263 | 263 | 0.041 | 0.041 | 0.041 | 0.96 | 0.96 |
| Marian | 0.014 | 0.014 | 0.014 | 279 | 270 | 270 | 6.07 | 6.07 | 6.07 | 0.99 | 0.99 |

One row per workload on two channels with the new front end; each value is the mean of its 4 slot runs. Measures as defined above. FCFS row-hit rates are under "Row hits under FCFS".

## Same as FR-FCFS alone

All 11 check runs match their reference in every gem5 statistic of all 10 dumps, so BLISS, ATLAS, TCM and SAA need no alone runs of their own. Each check is tealeaf from checkpoint slot 2, the heaviest workload, compared dump by dump with the reference run.

| Check run | Channels | Reference run | gem5 statistics that differ | Pool (SST) statistics that differ |
| --- | --- | --- | --- | --- |
| FR-FCFS, new front end | 1 | O3 FR-FCFS | 0 | 2 of 18 (front-end counters) |
| BLISS | 1 | O3 FR-FCFS | 0 | 2 of 18 (front-end counters) |
| ATLAS, 10M + rule | 1 | O3 FR-FCFS | 0 | 2 of 18 (front-end counters) |
| TCM | 1 | O3 FR-FCFS | 0 | 2 of 18 (front-end counters) |
| SAA, smoothing | 1 | O3 FR-FCFS | 0 | 2 of 18 (front-end counters) |
| FR-FCFS, second run | 2 | new FR-FCFS | 0 | 0 of 18 |
| BLISS | 2 | new FR-FCFS | 0 | 0 of 18 |
| ATLAS, 10M + rule | 2 | new FR-FCFS | 0 | 0 of 18 |
| TCM | 2 | new FR-FCFS | 0 | 0 of 18 |
| SAA, smoothing | 2 | new FR-FCFS | 0 | 0 of 18 |
| FCFS, second run | 2 | new FCFS | 0 | 0 of 14 |

One row per check run. gem5 statistics: every statistic in each of the 10 dumps except the host's own wall-clock timing. Pool statistics: the SST memory controller's statistics both runs report.

The two pool statistics that differ on one channel count how often the controller tried to issue and was refused (about 50 million cycles in the O3 run, 0 with the new front end) and the cycles in which it issued (about 9.9 million against 18.3 million). The new front end never offers a channel a request it cannot take, so these counters change their meaning; every request, its timing and every DRAM command count are the same. The 1-channel FR-FCFS row also shows the front end itself changes nothing with one host on one channel. The 2-channel second runs repeat the baseline runs exactly, so those runs are deterministic.

## The new 2-channel front end, one host

With one host the new front end changes little on two channels: 27 of 48 FCFS runs and 32 of 48 FR-FCFS runs are bit-identical to the O3 runs, and the rest differ by −2.98% to +1.67% in instruction rate. Only the five workloads with the most pool bandwidth differ at all, apart from one cactus slot.

| Workload | FCFS: runs identical to O3 (of 4) | FCFS: instr. rate change, slots 0 / 1 / 2 / 3 | FR-FCFS: runs identical to O3 (of 4) | FR-FCFS: instr. rate change, slots 0 / 1 / 2 / 3 |
| --- | --- | --- | --- | --- |
| tealeaf | 0 | −0.46% / +0.28% / +0.95% / +1.67% | 0 | +0.09% / −0.06% / +0.29% / −0.62% |
| STREAM | 0 | −0.34% / +0.56% / −2.98% / +0.29% | 2 | 0.00% / 0.00% / +1.65% / +0.86% |
| fotonik3d | 0 | −0.06% / +0.51% / +0.13% / 0.00% | 0 | −0.11% / −0.15% / −1.06% / −0.13% |
| streamcluster | 0 | +0.04% / −0.04% / +0.02% / +0.16% | 3 | +0.11% / 0.00% / 0.00% / 0.00% |
| roms | 0 | −0.20% / −0.15% / −0.04% / +0.05% | 0 | +0.05% / −0.60% / +0.08% / +0.01% |
| LLM inference | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |
| MERCI | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |
| graph500 | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |
| hnswlib | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |
| cactus | 3 | 0.00% / 0.00% / +0.02% / 0.00% | 3 | 0.00% / 0.00% / −0.10% / 0.00% |
| multichase | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |
| Marian | 4 | 0.00% / 0.00% / 0.00% / 0.00% | 4 | 0.00% / 0.00% / 0.00% / 0.00% |

One row per workload. Identical: the new run and the O3 run from the same checkpoint have the same committed instructions, pool requests and summed latency. Change: new front end ÷ O3 front end − 1 within each slot, same scheduler; 0.00% where the two runs are identical or differ by less than 0.005%.

- **Removing head-of-line blocking barely shows with one host.** The O3 front end held back a request only while the request ahead of it waited for a full channel's 32 pending slots. That the differences appear only in the heaviest workloads fits this; how often it happened was not counted.
- **Pool latency moves by under 1 ns.** No workload's mean latency changes by more than 0.6 ns under either scheduler, so for one host the new front end does not make the pool faster.
- **The FR-FCFS gain over FCFS is unchanged.** On two channels it stays between −2.6% (graph500) and +17.1% (MERCI), as in the O3 runs; tealeaf's moves from +7.2% to +6.5% and STREAM's from +7.2% to +8.6%.

## PAR-BS alone against FR-FCFS

PAR-BS alone costs tealeaf and STREAM 11.5% of their instruction rate on one channel, and MERCI 7.7% of its pool bandwidth; on two channels its largest cost is STREAM's 6.6% (MERCI read by pool bandwidth). Every loss of 1% or more comes with a lower row-hit rate.

| Workload | 1 ch: instr. rate | 1 ch: pool bandwidth | 1 ch: latency (ns) | 1 ch: row-hit rate, FR-FCFS → PAR-BS | 2 ch: instr. rate | 2 ch: pool bandwidth | 2 ch: latency (ns) | 2 ch: row-hit rate, FR-FCFS → PAR-BS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tealeaf | −11.5% | −11.3% | +50 | 0.74 → 0.63 | −1.1% | −1.4% | +5 | 0.47 → 0.44 |
| STREAM | −11.5% | −13.1% | +9 | 0.78 → 0.67 | −6.6% | −2.3% | +3 | 0.51 → 0.46 |
| fotonik3d | −1.0% | −1.4% | +3 | 0.74 → 0.71 | +0.1% | −0.1% | 0 | 0.61 → 0.60 |
| streamcluster | 0.0% | −0.1% | 0 | 0.91 → 0.90 | +0.1% | +0.1% | 0 | 0.85 → 0.85 |
| roms | −1.3% | −1.8% | +4 | 0.79 → 0.77 | −0.1% | −0.2% | +1 | 0.66 → 0.65 |
| LLM inference | 0.0% | 0.0% | 0 | 0.97 → 0.96 | 0.0% | −0.1% | 0 | 0.98 → 0.98 |
| MERCI | +2.2% | −7.7% | +2 | 0.82 → 0.71 | −14.5% | +0.3% | +2 | 0.55 → 0.53 |
| graph500 | 0.0% | 0.0% | 0 | 0.27 → 0.27 | 0.0% | 0.0% | 0 | 0.24 → 0.24 |
| hnswlib | −0.3% | 0.0% | +1 | 0.76 → 0.74 | +0.4% | +0.2% | 0 | 0.62 → 0.62 |
| cactus | +0.5% | +0.8% | −1 | 0.51 → 0.49 | −0.7% | −0.9% | +1 | 0.51 → 0.49 |
| multichase | −0.1% | 0.0% | 0 | 0.95 → 0.95 | 0.0% | 0.0% | 0 | 0.96 → 0.96 |
| Marian | 0.0% | 0.0% | 0 | 0.99 → 0.99 | 0.0% | 0.0% | 0 | 0.99 → 0.99 |

One row per workload. Instruction rate and pool bandwidth: PAR-BS ÷ FR-FCFS − 1 within each slot, mean of the 4 slots, against the O3 FR-FCFS runs on one channel and the new FR-FCFS runs on two. Latency: PAR-BS minus FR-FCFS, mean of the 4 slots. Row-hit rate: 4-slot means.

- **Batches hold back row hits.** When no batch request is left, PAR-BS marks the up to 5 oldest requests in every bank, and the bank serves marked requests before any row hit. A queued hit to the open row that missed the batch now waits behind the batch's misses, so a heavy streaming host gets fewer hits: tealeaf's rate falls from 0.74 to 0.63 and its latency rises 50 ns on one channel.
- **Light workloads barely change.** The six workloads under 4 GB/s other than MERCI change their instruction rate by 0.7% or less on either channel count. How many requests wait per bank was not counted, so whether the cap of 5 ever binds for them is not known.
- **MERCI is read by pool bandwidth.** Its instruction rate swings between phases and resets with its own statistics dumps, as the O3 alone report (doc 10) found, so its +2.2% and −14.5% say little; its pool bandwidth falls 7.4% to 7.9% in every 1-channel slot and changes −0.6% to +1.1% on two.
- **STREAM loses part through the L3 prefetcher.** As FR-FCFS's back-to-back row service fed the L3 stride prefetcher, PAR-BS's shorter runs feed it less (below).
- **Baseline matters for PAR-BS's mix slowdowns.** They are measured against these runs. Against the FR-FCFS alone runs instead, tealeaf's and STREAM's 1-channel slowdowns under PAR-BS would be about 13% higher (1 ÷ (1 − 0.115) = 1.13).

| Workload | L3 prefetches, 1 ch FR-FCFS | L3 prefetches, 1 ch PAR-BS | L3 demand misses, 1 ch FR-FCFS | L3 demand misses, 1 ch PAR-BS |
| --- | --- | --- | --- | --- |
| tealeaf | 24.6 | 18.7 | 9.9 | 11.3 |
| STREAM | 204.1 | 125.5 | 33.6 | 47.7 |
| fotonik3d | 39.7 | 37.7 | 16.5 | 16.9 |
| roms | 43.1 | 41.8 | 5.7 | 5.8 |
| MERCI | 51.8 | 38.6 | 10.8 | 11.2 |

One row per workload that loses 1% or more on one channel, each value the mean of its 4 slots, per 1000 instructions. Prefetches: lines issued by the host's L3 stride prefetcher. Demand misses: demand accesses that miss in the L3 and wait for memory. STREAM's prefetches fall by 39% and its demand misses rise by 42%; the O3 alone report (doc 10) found this prefetcher's training inflated by a gem5 flaw, so this part of the loss is the less reliable one.

## Slot to slot

PAR-BS's cost is steady across slots for STREAM (−11.3% to −11.6% on one channel, −6.0% to −7.3% on two) and varies for tealeaf (−8.0% to −14.6% on one channel). Elsewhere the slots differ by under 3 percentage points, apart from MERCI's instruction rate.

| Workload | 1 ch: instr. rate change, slots 0 / 1 / 2 / 3 | 1 ch: row-hit rate PAR-BS, slots 0–3 | 2 ch: instr. rate change, slots 0 / 1 / 2 / 3 | 2 ch: row-hit rate PAR-BS, slots 0–3 |
| --- | --- | --- | --- | --- |
| tealeaf | −13.22% / −10.17% / −8.04% / −14.60% | 0.63 / 0.63 / 0.63 / 0.62 | −1.00% / −0.67% / −1.56% / −1.02% | 0.44 / 0.44 / 0.44 / 0.44 |
| STREAM | −11.49% / −11.34% / −11.38% / −11.62% | 0.67 / 0.67 / 0.67 / 0.67 | −6.10% / −6.02% / −7.26% / −7.14% | 0.46 / 0.46 / 0.46 / 0.45 |
| fotonik3d | +0.15% / −1.90% / −2.26% / +0.05% | 0.69 / 0.71 / 0.71 / 0.75 | +0.01% / +0.23% / −0.01% / +0.07% | 0.59 / 0.60 / 0.59 / 0.62 |
| streamcluster | +0.19% / +0.05% / −0.16% / −0.10% | 0.91 / 0.89 / 0.90 / 0.91 | +0.04% / +0.46% / +0.16% / −0.18% | 0.85 / 0.85 / 0.85 / 0.85 |
| roms | −1.27% / −0.82% / −1.06% / −1.96% | 0.74 / 0.78 / 0.79 / 0.77 | −0.41% / +0.53% / −0.25% / −0.22% | 0.60 / 0.68 / 0.69 / 0.64 |
| LLM inference | −0.17% / +0.12% / +0.14% / −0.02% | 0.97 / 0.96 / 0.96 / 0.97 | −0.02% / +0.07% / −0.23% / +0.06% | 0.98 / 0.98 / 0.98 / 0.98 |
| MERCI | +0.43% / −2.79% / +4.14% / +7.12% | 0.72 / 0.71 / 0.71 / 0.72 | −22.61% / −9.88% / −16.31% / −9.13% | 0.53 / 0.54 / 0.52 / 0.53 |
| graph500 | −0.01% / 0.00% / −0.02% / +0.19% | 0.21 / 0.21 / 0.21 / 0.43 | −0.05% / 0.00% / +0.01% / +0.16% | 0.20 / 0.20 / 0.20 / 0.37 |
| hnswlib | +0.26% / −0.22% / −1.20% / −0.23% | 0.74 / 0.75 / 0.75 / 0.74 | +2.21% / +0.04% / −0.36% / −0.28% | 0.62 / 0.62 / 0.62 / 0.62 |
| cactus | 0.00% / +0.88% / +1.10% / 0.00% | 0.30 / 0.75 / 0.66 / 0.26 | 0.00% / −2.89% / +0.01% / −0.02% | 0.43 / 0.60 / 0.59 / 0.36 |
| multichase | 0.00% / 0.00% / 0.00% / −0.47% | 0.96 / 0.94 / 0.96 / 0.94 | 0.00% / 0.00% / 0.00% / 0.00% | 0.96 / 0.96 / 0.96 / 0.96 |
| Marian | 0.00% / 0.00% / 0.00% / 0.00% | 0.99 / 0.99 / 0.99 / 0.99 | 0.00% / 0.00% / 0.00% / 0.00% | 0.99 / 0.99 / 0.99 / 0.99 |

One row per workload. Instruction rate change: PAR-BS ÷ FR-FCFS − 1 within each slot, both runs from the same checkpoint; 0.00% where they are identical or differ by less than 0.005%. Row-hit rate: each slot's PAR-BS run.

- **tealeaf's row-hit rate is the same in every slot (0.62–0.63), yet its loss ranges from 8.0% to 14.6%.** The row-hit rate alone does not set the cost; what else differs between its slots was not traced.
- **cactus changes only in slots 1 and 2, and fotonik3d loses only there (−1.90% and −2.26% on one channel);** for cactus these are the high-bandwidth phase Phase 1 found. Slots 0 and 3 of both change by 0.15% or less. On two channels cactus's slot 1 loses 2.89%.
- **MERCI's instruction rate swings from −22.6% to −9.1% on two channels** while its pool bandwidth stays within −0.6% to +1.1%, which is why its pool bandwidth is the measure to use.

## Row hits under FCFS

FCFS with closed pages still finds the row open for 1% to 61% of accesses on two channels, so its row-hit rate is not 0; the O3 alone report (doc 10) said it was 0 by design. The bank precharges its row only when no command is in progress. While one is, it takes the next queued request, and a request to the same row is then served without a new activate.

| Workload | Row-hit rate, 2 ch FCFS (mean) | Slots 0 / 1 / 2 / 3 | Row-hit rate, 2 ch FR-FCFS (mean) |
| --- | --- | --- | --- |
| Marian | 0.61 | 0.61 / 0.64 / 0.61 / 0.60 | 0.99 |
| streamcluster | 0.43 | 0.42 / 0.43 / 0.43 / 0.43 | 0.85 |
| roms | 0.35 | 0.34 / 0.37 / 0.36 / 0.34 | 0.66 |
| hnswlib | 0.30 | 0.30 / 0.30 / 0.30 / 0.30 | 0.62 |
| LLM inference | 0.28 | 0.28 / 0.28 / 0.28 / 0.29 | 0.98 |
| fotonik3d | 0.21 | 0.23 / 0.20 / 0.21 / 0.20 | 0.61 |
| STREAM | 0.21 | 0.21 / 0.21 / 0.21 / 0.20 | 0.51 |
| tealeaf | 0.19 | 0.19 / 0.19 / 0.19 / 0.19 | 0.47 |
| graph500 | 0.13 | 0.11 / 0.11 / 0.11 / 0.18 | 0.24 |
| cactus | 0.12 | 0.01 / 0.24 / 0.23 / 0.01 | 0.51 |
| MERCI | 0.10 | 0.10 / 0.10 / 0.10 / 0.10 | 0.55 |
| multichase | 0.01 | 0.01 / 0.01 / 0.01 / 0.01 | 0.96 |

One row per workload on two channels with the new front end, sorted by the FCFS rate. Row-hit rate: 1 − activates ÷ column commands, counted by the btpmem copy of SST's bank code. FR-FCFS column for comparison, from the same runs as the results table.

The O3 FCFS runs used SST's stock code, which does not count activates, so their rates are unknown; the copy matches the stock code in every statistic in a check run, so they would have row hits too. The O3 alone report's FCFS latency arithmetic, a closed row on every access (about 22 ns), is therefore an upper bound. Its measured FCFS bandwidths, latencies and instruction rates are not affected.

## Caveats

- **One host per run.** These runs show what each scheduler does to a lone tenant. PAR-BS's batches and the front end's per-host queues exist for sharing, which only the mixes show.
- **PAR-BS's cap is the paper's value.** The cap of 5 requests per host per bank was not tuned; its alone cost depends on it.
- **MERCI's instruction rate.** MERCI resets gem5's statistics itself between its measured repeats, so its window means depend on where those resets fall. Its pool bandwidth is steadier and is its progress measure in the mixes.
- **The L3 prefetcher.** Part of STREAM's PAR-BS loss on one channel goes through the host's L3 stride prefetcher, whose per-core tables share one set of entries because of a gem5 flaw (see the O3 alone report (doc 10)). On a common server processor this part is likely smaller.
- **Fixed window.** The window is a fixed 100 ms, so a faster run reaches later phases sooner and its mean covers a different part of the program.
- **Check runs.** The equivalence check covers one workload in one slot per scheduler and channel count. It shows the code paths reduce to FR-FCFS with one host; it does not repeat that for every workload.
- **Covered time.** Some workloads reset or dump statistics themselves, so a run's periods cover 90 to 111 ms; every run reached the end of its window, and all rates are per simulated second over the covered periods.
