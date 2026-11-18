# Phase 1 – Mixed

Four hosts share one CXL pool channel (19.2 GB/s), each running a different workload from the final set of 12. Eighteen mixes span total demand from 3.0 to 23.9 GB/s, so the results cover no contention, near saturation and oversubscription.

## Setup and method

Every mix uses the same simulated setup as the alone runs, so each host's shared result compares directly with its alone baseline.

- **Hosts.** 4 hosts, each with 4 x86 cores at 3 GHz on gem5's timing CPU (in order, one demand miss per core; more requests in flight only from the prefetchers), with the same caches and cache miss limits as the alone runs.
- **Pool.** One DDR4-2400-like channel in SST: 1.2 GHz, 64 B per 4 data-bus cycles, so 19.2 GB/s theoretical peak; 2 ranks × 16 banks; about 245 ns unloaded round trip, almost all of it the fixed link delay. SST defaults throughout: one first-come-first-served front queue for all hosts, at most 32 requests in progress in the channel, FIFO bank queues and a closed-page policy.
- **Traffic.** Each workload's memory is bound to the pool with numactl. At least 99% of each memory-heavy host's memory bytes go to the pool; the rest is the guest OS on local memory. Marian is the exception at 94%, on 2 MB in total.
- **Slots.** Host i uses pool slot i (its own 1 GiB address range) and restores that workload's slot-i checkpoint. All 12 workloads have checkpoints for slots 0–3, taken with gem5's KVM CPU after boot and the workload's start-up. multichase uses the 15-sample checkpoints and Marian the 15 s ones.
- **Window.** 400 ms of simulated time from restore, statistics every 10 ms. All hosts run on one clock, so each window compares the same span of time on every host. Caches start cold at restore.
- **Simulation cost.** A mix took 2.5–4 hours on the desktop (i7-12700) and 17–19 hours on a cluster node, about 0.74–0.85 times the sum of its four alone runs on the same machine. Results are bit-identical across machines.

### How it was measured

- **Baselines.** Each host is compared with the same workload run alone from the same checkpoint slot, so guest state and pool address range match. All 48 workload-and-slot pairs were run, including the 13 no mix uses.
- **Rates.** Everything is per simulated second, so small differences in window length (390–443 ms) cancel.
- **Three measures, each the same for every host.** Pool latency is the mean round trip of the host's pool requests, including the 250 ns link. Instruction rate counts instructions committed by all of the host's cores. Request rate counts the pool requests the host completes. Each change is the mix value against the alone value of the same measure; no host's figure is swapped for a different measure.
- **Weighted speedup and Jain** use the instruction rate for all four hosts: weighted speedup adds each host's mix-to-alone instruction ratio (4 means no loss), and Jain's index is taken over the same ratios. MERCI and multichase are included as measured, so both summaries are slightly flattering where those two appear.
- **Checkpoint slot matters for three workloads.** cactus uses 0.25–1.53 GB/s alone depending on slot, graph500 uses 1.45 GB/s in slot 3 against 1.00 elsewhere, and fotonik3d uses 5.6–6.4 GB/s. Against slot-0 baselines, cactus's instruction rate would have looked 27% and 37% lower in mixes 16 and 12 (same-slot: 6% and 18%), and graph500's loss in mix 2 would have looked like 42% instead of 61%.
- **Mix 6 rerun.** The first streamcluster slot-2 checkpoint went idle after restore, both in the mix and alone. It was remade, checked with a short run, and mix 6 was rerun.

## The 18 mixes

Load is the sum of the four hosts' alone pool bandwidth, each from the checkpoint slot the host uses in the mix. The channel delivered at most 11.5 GB/s in any mix, so loads above about 12 GB/s ask for more than it serves. By slot-0 alone bandwidth, aggressors are tealeaf (T, 7.17 GB/s), STREAM (S, 6.59), fotonik3d (F, 5.58), streamcluster (SC, 4.17), roms (R, 3.63) and LLM inference (L, 2.61). Victims are merci4 (M, 0.96 in its region), graph500 BFS (G, 1.00), hnswlib (H, 0.41), cactus (C, 0.29), multichase (MC, 0.23) and Marian (MA, under 0.01).

| Mix | Group | Host 0 | Host 1 | Host 2 | Host 3 | Load (GB/s) | What it shows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 aggressors + 1 victim | tealeaf | STREAM | fotonik3d | multichase | 20.0 | Worst case: pure latency victim under full saturation |
| 2 | 3 aggressors + 1 victim | tealeaf | streamcluster | roms | graph500 BFS | 16.9 | Graph victim under mixed aggressor phases |
| 3 | 3 aggressors + 1 victim | STREAM | fotonik3d | LLM | hnswlib | 15.7 | RAG retrieval next to LLM decode (AI headline) |
| 4 | 3 aggressors + 1 victim | tealeaf | fotonik3d | roms | merci4 | 18.7 | Recommendation victim under bursty load |
| 5 | 3 aggressors + 1 victim | STREAM | streamcluster | LLM | cactus | 13.7 | Scientific victim at moderate load |
| 6 | 3 aggressors + 1 victim | tealeaf | fotonik3d | streamcluster | Marian | 17.4 | Whether a cache-friendly AI tenant is hurt at all |
| 7 | 2 aggressors + 2 victims | tealeaf | STREAM | hnswlib | multichase | 14.1 | Two strongest aggressors against two latency victims |
| 8 | 2 aggressors + 2 victims | fotonik3d | roms | graph500 BFS | cactus | 10.8 | Bursty and periodic aggressors, scientific victims |
| 9 | 2 aggressors + 2 victims | streamcluster | LLM | merci4 | Marian | 8.2 | AI-heavy, below saturation |
| 10 | 2 aggressors + 2 victims | tealeaf | LLM | hnswlib | multichase | 10.4 | An AI service pair next to a heavy aggressor |
| 11 | 2 aggressors + 2 victims | STREAM | roms | merci4 | graph500 BFS | 13.4 | Two victims that have some parallelism of their own |
| 12 | 2 aggressors + 2 victims | fotonik3d | streamcluster | cactus | Marian | 11.0 | Light victims under a peaky aggressor |
| 13 | 4 aggressors | tealeaf | STREAM | fotonik3d | streamcluster | 23.9 | Oversubscribed: how heavy users split the pool |
| 14 | 4 aggressors | fotonik3d | roms | LLM | streamcluster | 16.3 | Phase-changing aggressors near saturation |
| 15 | 1 aggressor + 3 victims | tealeaf | multichase | hnswlib | graph500 BFS | 9.3 | One heavy host among light ones |
| 16 | 1 aggressor + 3 victims | roms | merci4 | cactus | multichase | 6.5 | Periodic bursts into a mostly idle pool |
| 17 | All AI | LLM | merci4 | hnswlib | Marian | 4.4 | The four AI tenants together at low load |
| 18 | 4 victims (control) | merci4 | graph500 BFS | hnswlib | multichase | 3.0 | No contention (control) |

## Why these mixes

Under first-come-first-served service at the pool controller, a host's share follows how many requests it keeps in flight. Aggressors keep 15–42 in flight alone and victims 1–6, so mixes that pair them were expected to show victims losing far more than their share. Each group tests one part of that claim.

| Group | Mixes | What it tests |
| --- | --- | --- |
| 3 aggressors + 1 victim | 1–6 | The classic noisy-neighbour case, once for each victim |
| 2 aggressors + 2 victims | 7–12 | Victims that also compete with each other, at middle load |
| 4 aggressors | 13–14 | How heavy users split the pool between themselves |
| 1 aggressor + 3 victims | 15–16 | Light load with one heavy host |
| All AI | 17 | The AI pool on its own |
| 4 victims | 18 | Control with no contention |

The AI headline cases are mixes 3, 9, 10 and 17: no multi-host fairness study has put AI tenants on different hosts of one pool. Groups 4–6 are guard cases, which reviewers use to check that a fair scheduler costs nothing when the pool is not contended.

## Coverage

Every aggressor appears in 6–8 mixes and every victim in 4–6, each against a wide range of total load. A victim's slowdown can then be traced to load and to its neighbours' requests in flight, not to one pairing.

| Workload | Role | Mixes | Count | Total load across its mixes (GB/s) |
| --- | --- | --- | --- | --- |
| tealeaf | Aggressor | 1, 2, 4, 6, 7, 10, 13, 15 | 8 | 9.3–23.9 |
| fotonik3d | Aggressor | 1, 3, 4, 6, 8, 12, 13, 14 | 8 | 10.8–23.9 |
| streamcluster | Aggressor | 2, 5, 6, 9, 12, 13, 14 | 7 | 8.2–23.9 |
| STREAM | Aggressor | 1, 3, 5, 7, 11, 13 | 6 | 13.4–23.9 |
| roms | Aggressor | 2, 4, 8, 11, 14, 16 | 6 | 6.5–18.7 |
| LLM | Aggressor | 3, 5, 9, 10, 14, 17 | 6 | 4.4–16.3 |
| multichase | Victim | 1, 7, 10, 15, 16, 18 | 6 | 3.0–20.0 |
| hnswlib | Victim | 3, 7, 10, 15, 17, 18 | 6 | 3.0–15.7 |
| merci4 | Victim | 4, 9, 11, 16, 17, 18 | 6 | 3.0–18.7 |
| graph500 BFS | Victim | 2, 8, 11, 15, 18 | 5 | 3.0–16.9 |
| cactus | Victim | 5, 8, 12, 16 | 4 | 6.5–13.7 |
| Marian | Victim | 6, 9, 12, 17 | 4 | 4.4–17.4 |

multichase sees the widest range, from the idle control to full saturation, because it is the cleanest latency probe.

## Results

Each host is described by three measures, each computed the same way for every host and never substituted for one another: pool latency, instruction rate and pool request rate. Once a mix's workloads ask for more than about 13 GB/s, the single channel delivers 9.2–11.5 GB/s, every host's pool latency rises by 36–269%, and hosts lose 17–61% of their instruction rate.

- **Capacity.** The channel never delivered more than 11.5 GB/s, under 60% of its 19.2 GB/s nominal peak. Below 9 GB/s of demand, pool latency rose by at most 25% and every instruction rate stayed within 6% of alone.
- **Latency: every host waits about the same extra time.** In the heavy mixes, each request waits 200–850 ns longer than alone, and within one mix the extra wait differs by at most 1.7× between hosts. Light hosts start from 245–280 ns, so in percent their latency rises as much as or more than the heavy hosts'. In mix 1, multichase goes from 245 to 818 ns (+233%) and STREAM from 559 to 1,024 ns (+83%).
- **Instructions: the loss depends on how memory-bound a host is, not on its size.** graph500 loses 61% of its instruction rate in mix 2 and 59% in mix 11, against 21–40% for the other hosts there. Among the heavy hosts, fotonik3d loses 57–61% in mixes 1 and 13. Marian's instruction rate does not change even when its latency rises 180%, because it sends almost no traffic to the pool.
- **Requests: multichase and MERCI are only read by request rate.** Their instruction counts include spin and wait loops, so their instruction column understates the loss. multichase completes 67% fewer pool requests in mix 1 and 57% fewer in mix 7, while its instruction rate falls only 14% and 27%. The two columns are reported side by side; neither replaces the other.
- **Throughput and Jain.** Weighted speedup by instructions falls to 1.88–2.98 out of 4 above 13 GB/s; mix 13 keeps less than half. Jain's index by instructions stays at 0.93 or above, although in mix 2 graph500 loses 61% and tealeaf 26%. It hides the gap between hosts.
- **MERCI's instruction rate rises 14–16% in mixes 17 and 18**, while its request rate stays within 1%. This is the spin-loop effect, which is why weighted speedup by instructions goes slightly above 4 there.

Mixes, from highest to lowest demand. Every column uses one measure for all four hosts.

| Mix | Workloads (slots 0–3) | Demand alone (GB/s) | Pool delivered (GB/s) | Latency increase, lowest–highest host | Instruction rate change, worst host | Instruction rate change, best host | Weighted speedup by instructions (of 4) | Jain by instructions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | tealeaf, STREAM, fotonik3d, streamcluster | 23.9 | 10.7 | +96% to +269% | fotonik3d -61% | tealeaf -46% | 1.88 | 0.98 |
| 1 | tealeaf, STREAM, fotonik3d, multichase | 20.0 | 10.2 | +83% to +233% | fotonik3d -57% | multichase\* -14% | 2.44 | 0.94 |
| 4 | tealeaf, fotonik3d, roms, MERCI | 18.7 | 10.9 | +122% to +219% | fotonik3d -49% | MERCI\* -22% | 2.43 | 0.97 |
| 6 | tealeaf, fotonik3d, streamcluster, Marian | 17.4 | 10.6 | +91% to +180% | streamcluster -45% | Marian 0% | 2.81 | 0.94 |
| 2 | tealeaf, streamcluster, roms, graph500 | 16.9 | 10.9 | +64% to +123% | graph500 -61% | tealeaf -26% | 2.46 | 0.95 |
| 14 | fotonik3d, roms, LLM inference, streamcluster | 16.3 | 11.5 | +83% to +104% | streamcluster -34% | fotonik3d -20% | 2.98 | 0.99 |
| 3 | STREAM, fotonik3d, LLM inference, hnswlib | 15.7 | 10.0 | +52% to +160% | fotonik3d -41% | hnswlib -20% | 2.73 | 0.99 |
| 7 | tealeaf, STREAM, hnswlib, multichase | 14.1 | 9.3 | +53% to +181% | STREAM -35% | hnswlib -20% | 2.86 | 0.99 |
| 5 | STREAM, streamcluster, LLM inference, cactus | 13.7 | 9.4 | +36% to +96% | streamcluster -34% | cactus -17% | 2.94 | 0.99 |
| 11 | STREAM, roms, MERCI, graph500 | 13.4 | 9.2 | +38% to +114% | graph500 -59% | MERCI\* -5% | 2.87 | 0.93 |
| 12 | fotonik3d, streamcluster, cactus, Marian | 11.0 | 9.5 | +41% to +65% | streamcluster -20% | Marian 0% | 3.54 | 0.99 |
| 8 | fotonik3d, roms, graph500, cactus | 10.8 | 9.6 | +36% to +52% | graph500 -19% | fotonik3d -8% | 3.52 | 1.00 |
| 10 | tealeaf, LLM inference, hnswlib, multichase | 10.4 | 9.1 | +19% to +63% | LLM inference -15% | hnswlib -6% | 3.59 | 1.00 |
| 15 | tealeaf, multichase, hnswlib, graph500 | 9.3 | 8.3 | +11% to +50% | graph500 -24% | hnswlib -5% | 3.58 | 0.99 |
| 9 | streamcluster, LLM inference, MERCI, Marian | 8.2 | 7.7 | +8% to +15% | streamcluster -6% | Marian 0% | 3.88 | 1.00 |
| 16 | roms, MERCI, cactus, multichase | 6.5 | 6.2 | +8% to +25% | cactus -6% | multichase\* -3% | 3.82 | 1.00 |
| 17 | LLM inference, MERCI, hnswlib, Marian | 4.4 | 4.4 | +2% to +4% | LLM inference -1% | MERCI\* +14% | 4.14 | 1.00 |
| 18 | MERCI, graph500, hnswlib, multichase | 3.0 | 3.0 | +1% to +3% | graph500 -1% | MERCI\* +16% | 4.16 | 1.00 |

\* instruction count includes spin and wait loops; read this host by its request rate in the table below.

### Every host

All 72 hosts, in the same mix order. Each pair of columns compares the host with its own alone run from the same checkpoint slot, using one measure.

| Mix | Slot | Workload | Pool latency alone → mix (ns) | Latency increase | Instructions alone → mix (billion/s) | Instruction rate change | Pool requests alone → mix (million/s) | Request rate change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | 0 | tealeaf | 461 → 1151 | +150% | 5.001 → 2.703 | -46% | 111.99 → 60.75 | -46% |
| 13 | 1 | STREAM | 559 → 1094 | +96% | 0.908 → 0.473 | -48% | 98.70 → 48.28 | -51% |
| 13 | 2 | fotonik3d | 354 → 1199 | +239% | 2.801 → 1.099 | -61% | 97.88 → 36.86 | -62% |
| 13 | 3 | streamcluster | 294 → 1086 | +269% | 2.906 → 1.231 | -58% | 65.10 → 21.85 | -66% |
| 1 | 0 | tealeaf | 461 → 1067 | +132% | 5.001 → 2.845 | -43% | 111.99 → 65.01 | -42% |
| 1 | 1 | STREAM | 559 → 1024 | +83% | 0.908 → 0.525 | -42% | 98.70 → 51.91 | -47% |
| 1 | 2 | fotonik3d | 354 → 1098 | +210% | 2.801 → 1.218 | -57% | 97.88 → 41.53 | -58% |
| 1 | 3 | multichase\* | 245 → 818 | +233% | 0.019 → 0.017 | -14% | 3.66 → 1.20 | -67% |
| 4 | 0 | tealeaf | 461 → 1025 | +122% | 5.001 → 2.923 | -42% | 111.99 → 66.97 | -40% |
| 4 | 1 | fotonik3d | 353 → 1061 | +201% | 2.678 → 1.368 | -49% | 94.73 → 49.79 | -47% |
| 4 | 2 | roms | 316 → 923 | +192% | 4.228 → 2.327 | -45% | 63.65 → 40.97 | -36% |
| 4 | 3 | MERCI\* | 281 → 897 | +219% | 0.451 → 0.353 | -22% | 21.86 → 13.02 | -40% |
| 6 | 0 | tealeaf | 461 → 880 | +91% | 5.001 → 3.307 | -34% | 111.99 → 74.13 | -34% |
| 6 | 1 | fotonik3d | 353 → 969 | +174% | 2.678 → 1.587 | -41% | 94.73 → 60.31 | -36% |
| 6 | 2 | streamcluster | 294 → 772 | +163% | 2.907 → 1.607 | -45% | 65.04 → 30.36 | -53% |
| 6 | 3 | Marian | 278 → 778 | +180% | 1.809 → 1.808 | 0% | 0.07 → 0.07 | 0% |
| 2 | 0 | tealeaf | 461 → 758 | +64% | 5.001 → 3.711 | -26% | 111.99 → 82.18 | -27% |
| 2 | 1 | streamcluster | 294 → 657 | +123% | 2.905 → 1.748 | -40% | 65.07 → 33.65 | -48% |
| 2 | 2 | roms | 316 → 697 | +121% | 4.228 → 3.087 | -27% | 63.65 → 45.26 | -29% |
| 2 | 3 | graph500 | 277 → 520 | +88% | 0.764 → 0.296 | -61% | 22.65 → 8.93 | -61% |
| 14 | 0 | fotonik3d | 353 → 719 | +104% | 2.416 → 1.940 | -20% | 87.13 → 68.08 | -22% |
| 14 | 1 | roms | 319 → 633 | +99% | 4.229 → 3.356 | -21% | 61.45 → 44.26 | -28% |
| 14 | 2 | LLM inference | 283 → 518 | +83% | 6.555 → 4.777 | -27% | 41.49 → 29.06 | -30% |
| 14 | 3 | streamcluster | 294 → 581 | +98% | 2.906 → 1.907 | -34% | 65.10 → 37.63 | -42% |
| 3 | 0 | STREAM | 534 → 812 | +52% | 0.929 → 0.637 | -31% | 103.04 → 67.87 | -34% |
| 3 | 1 | fotonik3d | 353 → 815 | +131% | 2.678 → 1.590 | -41% | 94.73 → 60.89 | -36% |
| 3 | 2 | LLM inference | 283 → 633 | +124% | 6.555 → 4.266 | -35% | 41.49 → 24.39 | -41% |
| 3 | 3 | hnswlib | 269 → 699 | +160% | 1.314 → 1.054 | -20% | 6.34 → 3.86 | -39% |
| 7 | 0 | tealeaf | 461 → 846 | +84% | 5.001 → 3.419 | -32% | 111.99 → 75.89 | -32% |
| 7 | 1 | STREAM | 559 → 854 | +53% | 0.908 → 0.594 | -35% | 98.70 → 64.50 | -35% |
| 7 | 2 | hnswlib | 269 → 755 | +181% | 1.307 → 1.045 | -20% | 6.27 → 3.70 | -41% |
| 7 | 3 | multichase\* | 245 → 611 | +149% | 0.019 → 0.014 | -27% | 3.66 → 1.56 | -57% |
| 5 | 0 | STREAM | 534 → 728 | +36% | 0.929 → 0.663 | -29% | 103.04 → 77.09 | -25% |
| 5 | 1 | streamcluster | 294 → 578 | +96% | 2.905 → 1.904 | -34% | 65.07 → 37.43 | -42% |
| 5 | 2 | LLM inference | 283 → 536 | +90% | 6.555 → 4.909 | -25% | 41.49 → 28.36 | -32% |
| 5 | 3 | cactus | 271 → 495 | +83% | 1.561 → 1.290 | -17% | 3.90 → 3.24 | -17% |
| 11 | 0 | STREAM | 534 → 739 | +38% | 0.929 → 0.673 | -28% | 103.04 → 75.09 | -27% |
| 11 | 1 | roms | 319 → 635 | +99% | 4.229 → 3.338 | -21% | 61.45 → 44.09 | -28% |
| 11 | 2 | MERCI\* | 279 → 598 | +114% | 0.453 → 0.428 | -5% | 21.93 → 15.94 | -27% |
| 11 | 3 | graph500 | 277 → 477 | +72% | 0.764 → 0.314 | -59% | 22.65 → 9.33 | -59% |
| 12 | 0 | fotonik3d | 353 → 527 | +49% | 2.416 → 2.227 | -8% | 87.13 → 81.43 | -7% |
| 12 | 1 | streamcluster | 294 → 414 | +41% | 2.905 → 2.326 | -20% | 65.07 → 48.44 | -26% |
| 12 | 2 | cactus | 372 → 615 | +65% | 1.103 → 0.902 | -18% | 19.71 → 18.24 | -7% |
| 12 | 3 | Marian | 278 → 419 | +51% | 1.809 → 1.809 | 0% | 0.07 → 0.07 | 0% |
| 8 | 0 | fotonik3d | 353 → 532 | +51% | 2.416 → 2.226 | -8% | 87.13 → 81.35 | -7% |
| 8 | 1 | roms | 319 → 485 | +52% | 4.229 → 3.733 | -12% | 61.45 → 52.01 | -15% |
| 8 | 2 | graph500 | 256 → 347 | +36% | 0.507 → 0.409 | -19% | 15.59 → 12.53 | -20% |
| 8 | 3 | cactus | 271 → 378 | +40% | 1.561 → 1.420 | -9% | 3.90 → 3.55 | -9% |
| 10 | 0 | tealeaf | 461 → 550 | +19% | 5.001 → 4.517 | -10% | 111.99 → 101.91 | -9% |
| 10 | 1 | LLM inference | 283 → 421 | +49% | 6.537 → 5.571 | -15% | 41.34 → 33.56 | -19% |
| 10 | 2 | hnswlib | 269 → 437 | +63% | 1.307 → 1.226 | -6% | 6.27 → 4.65 | -26% |
| 10 | 3 | multichase\* | 245 → 334 | +36% | 0.019 → 0.017 | -10% | 3.66 → 2.76 | -25% |
| 15 | 0 | tealeaf | 461 → 511 | +11% | 5.001 → 4.734 | -5% | 111.99 → 105.43 | -6% |
| 15 | 1 | multichase\* | 245 → 315 | +29% | 0.016 → 0.015 | -8% | 3.66 → 2.91 | -20% |
| 15 | 2 | hnswlib | 269 → 402 | +50% | 1.307 → 1.239 | -5% | 6.27 → 4.84 | -23% |
| 15 | 3 | graph500 | 277 → 378 | +37% | 0.764 → 0.581 | -24% | 22.65 → 17.13 | -24% |
| 9 | 0 | streamcluster | 294 → 318 | +8% | 2.910 → 2.735 | -6% | 65.17 → 59.46 | -9% |
| 9 | 1 | LLM inference | 283 → 305 | +8% | 6.537 → 6.363 | -3% | 41.34 → 39.98 | -3% |
| 9 | 2 | MERCI\* | 279 → 321 | +15% | 0.453 → 0.439 | -3% | 21.93 → 21.02 | -4% |
| 9 | 3 | Marian | 278 → 306 | +10% | 1.809 → 1.809 | 0% | 0.07 → 0.07 | 0% |
| 16 | 0 | roms | 329 → 381 | +16% | 4.013 → 3.874 | -3% | 56.76 → 52.93 | -7% |
| 16 | 1 | MERCI\* | 284 → 312 | +10% | 0.435 → 0.410 | -6% | 21.99 → 20.65 | -6% |
| 16 | 2 | cactus | 372 → 464 | +25% | 1.103 → 1.039 | -6% | 19.71 → 19.24 | -2% |
| 16 | 3 | multichase\* | 245 → 265 | +8% | 0.019 → 0.019 | -3% | 3.66 → 3.42 | -7% |
| 17 | 0 | LLM inference | 283 → 289 | +2% | 6.539 → 6.481 | -1% | 40.76 → 40.26 | -1% |
| 17 | 1 | MERCI\* | 284 → 292 | +3% | 0.435 → 0.496 | +14% | 21.99 → 21.93 | 0% |
| 17 | 2 | hnswlib | 269 → 277 | +3% | 1.307 → 1.322 | +1% | 6.27 → 6.04 | -4% |
| 17 | 3 | Marian | 278 → 290 | +4% | 1.809 → 1.809 | 0% | 0.07 → 0.07 | 0% |
| 18 | 0 | MERCI\* | 279 → 288 | +3% | 0.441 → 0.513 | +16% | 21.82 → 22.01 | +1% |
| 18 | 1 | graph500 | 256 → 258 | +1% | 0.502 → 0.500 | -1% | 15.62 → 15.53 | -1% |
| 18 | 2 | hnswlib | 269 → 274 | +2% | 1.307 → 1.315 | +1% | 6.27 → 6.11 | -2% |
| 18 | 3 | multichase\* | 245 → 248 | +1% | 0.019 → 0.019 | 0% | 3.66 → 3.63 | -1% |

\* instruction count includes spin and wait loops, so the instruction rate does not track useful work; use the request rate.

### Fairness across hosts

How fair the pool looks depends on what is measured. In the ten mixes above 13 GB/s, Jain's index stays at 0.93–0.99 on instruction rate, request rate and mean latency, but falls to 0.81–0.97 on p95 latency, 0.79–0.92 on bandwidth against a fair share and 0.55–0.96 on extra queue wait. The worst-hit host slows about 1.9 times as much as the least-hit one in mixes 2, 7 and 11.

| Mix | Workloads (slots 0–3) | Demand alone (GB/s) | Pool delivered (GB/s) | Max slowdown (host) | Min slowdown | Unfairness (max/min) | Jain: instructions | Jain: requests | Jain: mean latency | Jain: extra wait | Jain: p95 latency | Jain: bandwidth vs fair share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | tealeaf, STREAM, fotonik3d, streamcluster | 23.9 | 10.7 | 2.55 (fotonik3d) | 1.85 | 1.38 | 0.98 | 0.96 | 0.94 | 0.73 | 0.86 | 0.90 |
| 1 | tealeaf, STREAM, fotonik3d, multichase\* | 20.0 | 10.2 | 3.05 (multichase) | 1.73 | 1.76 | 0.94 | 0.96 | 0.94 | 0.65 | 0.85 | 0.86 |
| 4 | tealeaf, fotonik3d, roms, MERCI\* | 18.7 | 10.9 | 1.96 (fotonik3d) | 1.68 | 1.17 | 0.97 | 0.99 | 0.98 | 0.75 | 0.93 | 0.92 |
| 6 | tealeaf, fotonik3d, streamcluster, Marian | 17.4 | 10.6 | 1.81 (streamcluster) | 1.51 | 1.20 | 0.94 | 0.93 | 0.97 | 0.69 | 0.88 | 0.92 |
| 2 | tealeaf, streamcluster, roms, graph500 | 16.9 | 10.9 | 2.58 (graph500) | 1.35 | 1.91 | 0.95 | 0.95 | 0.98 | 0.72 | 0.90 | 0.79 |
| 14 | fotonik3d, roms, LLM inference, streamcluster | 16.3 | 11.5 | 1.52 (streamcluster) | 1.25 | 1.22 | 0.99 | 0.99 | 1.00 | 0.96 | 0.97 | 0.92 |
| 3 | STREAM, fotonik3d, LLM inference, hnswlib | 15.7 | 10.0 | 1.68 (fotonik3d) | 1.25 | 1.35 | 0.99 | 1.00 | 0.95 | 0.58 | 0.85 | 0.90 |
| 7 | tealeaf, STREAM, hnswlib, multichase\* | 14.1 | 9.3 | 2.34 (multichase) | 1.25 | 1.87 | 0.99 | 0.97 | 0.94 | 0.55 | 0.83 | 0.89 |
| 5 | STREAM, streamcluster, LLM inference, cactus | 13.7 | 9.4 | 1.53 (streamcluster) | 1.21 | 1.26 | 0.99 | 0.98 | 0.98 | 0.59 | 0.81 | 0.89 |
| 11 | STREAM, roms, MERCI\*, graph500 | 13.4 | 9.2 | 2.43 (graph500) | 1.27 | 1.92 | 0.93 | 0.96 | 0.97 | 0.63 | 0.86 | 0.83 |
| 12 | fotonik3d, streamcluster, cactus, Marian | 11.0 | 9.5 | 1.25 (streamcluster) | 1.09 | 1.15 | 0.99 | 0.99 | 1.00 | 0.95 | 0.96 | 0.97 |
| 8 | fotonik3d, roms, graph500, cactus | 10.8 | 9.6 | 1.24 (graph500) | 1.09 | 1.14 | 1.00 | 1.00 | 1.00 | 0.85 | 0.97 | 0.98 |
| 10 | tealeaf, LLM inference, hnswlib, multichase\* | 10.4 | 9.1 | 1.33 (multichase) | 1.07 | 1.24 | 1.00 | 0.99 | 0.99 | 0.54 | 0.91 | 0.97 |
| 15 | tealeaf, multichase\*, hnswlib, graph500 | 9.3 | 8.3 | 1.31 (graph500) | 1.05 | 1.25 | 0.99 | 0.99 | 0.99 | 0.54 | 0.92 | 0.98 |
| 9 | streamcluster, LLM inference, MERCI\*, Marian | 8.2 | 7.7 | 1.06 (streamcluster) | 1.03 | 1.04 | 1.00 | 1.00 | 1.00 | 0.98 | 0.99 | 1.00 |
| 16 | roms, MERCI\*, cactus, multichase\* | 6.5 | 6.2 | 1.07 (multichase) | 1.04 | 1.03 | 1.00 | 1.00 | 1.00 | 0.92 | 1.00 | 1.00 |
| 17 | LLM inference, MERCI\*, hnswlib, Marian | 4.4 | 4.4 | 1.01 (LLM inference) | 0.99 | 1.02 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 18 | MERCI\*, graph500, hnswlib, multichase\* | 3.0 | 3.0 | 1.01 (multichase) | 0.99 | 1.02 | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 |

\* progress for this host's slowdown is its pool request rate, because its instruction count includes spin and wait loops.

- **Slowdown** is alone progress ÷ mix progress. Progress is the instruction rate, or the pool request rate for MERCI and multichase. **Unfairness** is the largest slowdown ÷ the smallest in the mix, leaving out Marian, which sends almost no traffic to the pool and never slows.
- **Jain's index** is (Σx)² ÷ (n × Σx²) over the four hosts' kept-ratios x, where 1 means unaffected. It is 1.00 when every host keeps the same fraction and falls toward 0.25 as one host loses everything. With four hosts, one host kept at half the others' level still scores 0.94.
- **Kept-ratios.** Instructions and requests: mix rate ÷ alone rate. Mean and p95 latency: alone ÷ mix. Extra wait: alone wait ÷ mix wait, where wait is round-trip latency minus the 245 ns unloaded latency, floored at 5 ns. Bandwidth vs fair share: bandwidth received ÷ the max-min fair share of what the pool delivered in that mix, with each host's alone bandwidth as its demand.
- **Extra wait exaggerates light hosts.** multichase waits under 1 ns alone, so any queueing makes its ratio small; Jain on extra wait is 0.54 even in mixes 10 and 15.
- **Who loses bandwidth.** In mixes 2 and 11, graph500 receives 0.39–0.41 of its fair share while tealeaf and STREAM receive 1.5–1.7 times theirs. multichase receives 0.33 of its share in mix 1 and 0.43 in mix 7.

### Tail latency per host

Queueing stretches the tail more than the mean. In the mixes above 13 GB/s, p95 rises 1.2–5.4 times (median 2.8 times); multichase's p95 in mix 1 goes from 312 to 1,702 ns. The latency histogram ends at 2 µs: in mixes 1, 3, 4, 6, 12 and 13, more than 1% of some hosts' requests exceed it, so their p99 is shown as >2000 ns and only p95 and below are exact.

| Mix | Slot | Workload | p50 alone → mix (ns) | p90 alone → mix (ns) | p95 alone → mix (ns) | p99 alone → mix (ns) | Requests over 2 µs in mix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | 0 | tealeaf | 362 → 1078 | 752 → 1708 | 892 → 1938 | 1362 → >2000 | 4.1% |
| 13 | 1 | STREAM | 462 → 1048 | 1068 → 1598 | 1172 → 1798 | 1538 → >2000 | 2.4% |
| 13 | 2 | fotonik3d | 308 → 1198 | 508 → 1728 | 608 → 1912 | 858 → >2000 | 3.5% |
| 13 | 3 | streamcluster | 282 → 1052 | 332 → 1552 | 358 → 1728 | 438 → >2000 | 1.7% |
| 1 | 0 | tealeaf | 362 → 992 | 752 → 1602 | 892 → 1818 | 1362 → >2000 | 2.7% |
| 1 | 1 | STREAM | 462 → 972 | 1068 → 1522 | 1172 → 1728 | 1538 → >2000 | 2.1% |
| 1 | 2 | fotonik3d | 308 → 1102 | 508 → 1572 | 608 → 1732 | 858 → >2000 | 1.6% |
| 1 | 3 | multichase | 248 → 722 | 248 → 1392 | 312 → 1702 | 458 → >2000 | 2.7% |
| 4 | 0 | tealeaf | 362 → 938 | 752 → 1608 | 892 → 1862 | 1362 → >2000 | 3.4% |
| 4 | 1 | fotonik3d | 308 → 1072 | 508 → 1598 | 608 → 1768 | 858 → >2000 | 1.9% |
| 4 | 2 | roms | 288 → 868 | 388 → 1452 | 448 → 1642 | 622 → >2000 | 1.2% |
| 4 | 3 | MERCI | 232 → 848 | 328 → 1382 | 368 → 1588 | 602 → >2000 | 1.3% |
| 6 | 0 | tealeaf | 362 → 742 | 752 → 1572 | 892 → 1842 | 1362 → >2000 | 3.2% |
| 6 | 1 | fotonik3d | 308 → 1008 | 508 → 1542 | 608 → 1712 | 858 → >2000 | 1.5% |
| 6 | 2 | streamcluster | 282 → 678 | 332 → 1372 | 358 → 1568 | 432 → 1972 | 0.9% |
| 6 | 3 | Marian | 272 → 678 | 302 → 1408 | 308 → 1602 | 532 → >2000 | 1.2% |
| 2 | 0 | tealeaf | 362 → 712 | 752 → 1162 | 892 → 1328 | 1362 → 1722 | 0.3% |
| 2 | 1 | streamcluster | 282 → 622 | 332 → 1028 | 358 → 1168 | 438 → 1478 | 0.1% |
| 2 | 2 | roms | 288 → 668 | 388 → 1062 | 448 → 1208 | 622 → 1528 | 0.1% |
| 2 | 3 | graph500 | 272 → 468 | 328 → 872 | 358 → 1012 | 482 → 1342 | 0.0% |
| 14 | 0 | fotonik3d | 308 → 708 | 512 → 1152 | 612 → 1312 | 862 → 1722 | 0.4% |
| 14 | 1 | roms | 292 → 542 | 392 → 1082 | 458 → 1252 | 652 → 1662 | 0.3% |
| 14 | 2 | LLM inference | 272 → 422 | 308 → 898 | 318 → 1038 | 362 → 1362 | 0.1% |
| 14 | 3 | streamcluster | 282 → 488 | 332 → 1012 | 358 → 1172 | 438 → 1562 | 0.2% |
| 3 | 0 | STREAM | 458 → 708 | 952 → 1358 | 1132 → 1572 | 1518 → >2000 | 1.2% |
| 3 | 1 | fotonik3d | 308 → 802 | 508 → 1272 | 608 → 1432 | 858 → 1868 | 0.6% |
| 3 | 2 | LLM inference | 272 → 568 | 308 → 1048 | 318 → 1208 | 362 → 1588 | 0.2% |
| 3 | 3 | hnswlib | 272 → 628 | 352 → 1232 | 458 → 1468 | 542 → >2000 | 1.2% |
| 7 | 0 | tealeaf | 362 → 788 | 752 → 1262 | 892 → 1472 | 1362 → 1938 | 0.8% |
| 7 | 1 | STREAM | 462 → 788 | 1068 → 1312 | 1172 → 1488 | 1538 → 1932 | 0.8% |
| 7 | 2 | hnswlib | 272 → 712 | 352 → 1232 | 458 → 1458 | 542 → 1992 | 1.0% |
| 7 | 3 | multichase | 248 → 548 | 248 → 1012 | 312 → 1242 | 458 → 1788 | 0.5% |
| 5 | 0 | STREAM | 458 → 628 | 952 → 1222 | 1132 → 1382 | 1518 → 1772 | 0.5% |
| 5 | 1 | streamcluster | 282 → 528 | 332 → 898 | 358 → 1032 | 438 → 1412 | 0.1% |
| 5 | 2 | LLM inference | 272 → 488 | 308 → 822 | 318 → 958 | 362 → 1332 | 0.1% |
| 5 | 3 | cactus | 272 → 438 | 272 → 792 | 272 → 928 | 278 → 1292 | 0.1% |
| 11 | 0 | STREAM | 458 → 648 | 952 → 1202 | 1132 → 1348 | 1518 → 1732 | 0.4% |
| 11 | 1 | roms | 292 → 588 | 392 → 962 | 458 → 1112 | 652 → 1488 | 0.1% |
| 11 | 2 | MERCI | 232 → 518 | 328 → 932 | 362 → 1098 | 568 → 1492 | 0.1% |
| 11 | 3 | graph500 | 272 → 428 | 328 → 778 | 358 → 918 | 482 → 1272 | 0.0% |
| 12 | 0 | fotonik3d | 308 → 432 | 512 → 922 | 612 → 1148 | 862 → 1602 | 0.2% |
| 12 | 1 | streamcluster | 282 → 322 | 332 → 678 | 358 → 862 | 438 → 1388 | 0.1% |
| 12 | 2 | cactus | 292 → 402 | 622 → 1358 | 848 → 1598 | 1238 → >2000 | 1.2% |
| 12 | 3 | Marian | 272 → 308 | 302 → 732 | 308 → 948 | 532 → 1542 | 0.1% |
| 8 | 0 | fotonik3d | 308 → 468 | 512 → 902 | 612 → 1048 | 862 → 1408 | 0.1% |
| 8 | 1 | roms | 292 → 372 | 392 → 848 | 458 → 1008 | 652 → 1388 | 0.1% |
| 8 | 2 | graph500 | 268 → 278 | 298 → 588 | 322 → 742 | 372 → 1078 | 0.0% |
| 8 | 3 | cactus | 272 → 282 | 272 → 648 | 272 → 788 | 278 → 1098 | 0.0% |
| 10 | 0 | tealeaf | 362 → 458 | 752 → 902 | 892 → 1052 | 1362 → 1488 | 0.1% |
| 10 | 1 | LLM inference | 272 → 342 | 308 → 672 | 318 → 792 | 362 → 1088 | 0.0% |
| 10 | 2 | hnswlib | 272 → 372 | 352 → 772 | 458 → 938 | 542 → 1332 | 0.1% |
| 10 | 3 | multichase | 248 → 258 | 248 → 542 | 312 → 672 | 458 → 1042 | 0.0% |
| 15 | 0 | tealeaf | 362 → 408 | 752 → 842 | 892 → 992 | 1362 → 1462 | 0.1% |
| 15 | 1 | multichase | 248 → 252 | 248 → 492 | 322 → 618 | 458 → 988 | 0.0% |
| 15 | 2 | hnswlib | 272 → 338 | 352 → 708 | 458 → 868 | 542 → 1262 | 0.1% |
| 15 | 3 | graph500 | 272 → 298 | 328 → 628 | 358 → 778 | 482 → 1112 | 0.0% |
| 9 | 0 | streamcluster | 282 → 298 | 332 → 382 | 358 → 438 | 438 → 602 | 0.0% |
| 9 | 1 | LLM inference | 272 → 282 | 308 → 358 | 318 → 408 | 362 → 558 | 0.0% |
| 9 | 2 | MERCI | 232 → 258 | 328 → 422 | 362 → 532 | 568 → 772 | 0.0% |
| 9 | 3 | Marian | 272 → 282 | 302 → 382 | 308 → 478 | 532 → 612 | 0.0% |
| 16 | 0 | roms | 292 → 312 | 422 → 572 | 502 → 752 | 742 → 1178 | 0.0% |
| 16 | 1 | MERCI | 232 → 258 | 328 → 388 | 382 → 502 | 628 → 802 | 0.0% |
| 16 | 2 | cactus | 292 → 328 | 622 → 932 | 848 → 1148 | 1238 → 1548 | 0.1% |
| 16 | 3 | multichase | 248 → 248 | 248 → 322 | 312 → 388 | 458 → 688 | 0.0% |
| 17 | 0 | LLM inference | 272 → 278 | 308 → 318 | 318 → 342 | 362 → 422 | 0.0% |
| 17 | 1 | MERCI | 232 → 248 | 328 → 352 | 382 → 408 | 628 → 608 | 0.0% |
| 17 | 2 | hnswlib | 272 → 278 | 352 → 382 | 458 → 478 | 542 → 568 | 0.0% |
| 17 | 3 | Marian | 272 → 278 | 302 → 328 | 308 → 378 | 532 → 538 | 0.0% |
| 18 | 0 | MERCI | 232 → 242 | 322 → 342 | 362 → 382 | 572 → 608 | 0.0% |
| 18 | 1 | graph500 | 268 → 272 | 298 → 308 | 322 → 332 | 372 → 388 | 0.0% |
| 18 | 2 | hnswlib | 272 → 278 | 352 → 368 | 458 → 472 | 542 → 558 | 0.0% |
| 18 | 3 | multichase | 248 → 248 | 248 → 258 | 312 → 322 | 458 → 452 | 0.0% |

Percentiles come from each host's histogram of pool round-trip latency, with 5 ns buckets from 0 to 2 µs over the whole 400 ms window; each value is its bucket's midpoint.
