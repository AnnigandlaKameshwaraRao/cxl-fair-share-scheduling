| Mix | Workloads (slots 0–3) | Demand alone (GB/s) | Pool delivered (GB/s) | Latency increase, lowest–highest host | Instruction rate change, worst host | Instruction rate change, best host | Weighted speedup by instructions (of 4) | Jain by instructions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | tealeaf, STREAM, fotonik3d, streamcluster | 23.9 | 10.7 | +96% to +269% | fotonik3d -61% | tealeaf -46% | 1.88 | 0.98 |
| 1 | tealeaf, STREAM, fotonik3d, multichase | 20.0 | 10.2 | +83% to +233% | fotonik3d -57% | multichase -14% | 2.44 | 0.94 |
| 4 | tealeaf, fotonik3d, roms, MERCI | 18.7 | 10.9 | +122% to +219% | fotonik3d -49% | MERCI -22% | 2.43 | 0.97 |
| 6 | tealeaf, fotonik3d, streamcluster, Marian | 17.4 | 10.6 | +91% to +180% | streamcluster -45% | Marian 0% | 2.81 | 0.94 |
| 2 | tealeaf, streamcluster, roms, graph500 | 16.9 | 10.9 | +64% to +123% | graph500 -61% | tealeaf -26% | 2.46 | 0.95 |
| 14 | fotonik3d, roms, LLM inference, streamcluster | 16.3 | 11.5 | +83% to +104% | streamcluster -34% | fotonik3d -20% | 2.98 | 0.99 |
| 3 | STREAM, fotonik3d, LLM inference, hnswlib | 15.7 | 10.0 | +52% to +160% | fotonik3d -41% | hnswlib -20% | 2.73 | 0.99 |
| 7 | tealeaf, STREAM, hnswlib, multichase | 14.1 | 9.3 | +53% to +181% | STREAM -35% | hnswlib -20% | 2.86 | 0.99 |
| 5 | STREAM, streamcluster, LLM inference, cactus | 13.7 | 9.4 | +36% to +96% | streamcluster -34% | cactus -17% | 2.94 | 0.99 |
| 11 | STREAM, roms, MERCI, graph500 | 13.4 | 9.2 | +38% to +114% | graph500 -59% | MERCI -5% | 2.87 | 0.93 |
| 12 | fotonik3d, streamcluster, cactus, Marian | 11.0 | 9.5 | +41% to +65% | streamcluster -20% | Marian 0% | 3.54 | 0.99 |
| 8 | fotonik3d, roms, graph500, cactus | 10.8 | 9.6 | +36% to +52% | graph500 -19% | fotonik3d -8% | 3.52 | 1.00 |
| 10 | tealeaf, LLM inference, hnswlib, multichase | 10.4 | 9.1 | +19% to +63% | LLM inference -15% | hnswlib -6% | 3.59 | 1.00 |
| 15 | tealeaf, multichase, hnswlib, graph500 | 9.3 | 8.3 | +11% to +50% | graph500 -24% | hnswlib -5% | 3.58 | 0.99 |
| 9 | streamcluster, LLM inference, MERCI, Marian | 8.2 | 7.7 | +8% to +15% | streamcluster -6% | Marian 0% | 3.88 | 1.00 |
| 16 | roms, MERCI, cactus, multichase | 6.5 | 6.2 | +8% to +25% | cactus -6% | multichase -3% | 3.82 | 1.00 |
| 17 | LLM inference, MERCI, hnswlib, Marian | 4.4 | 4.4 | +2% to +4% | LLM inference -1% | MERCI +14% | 4.14 | 1.00 |
| 18 | MERCI, graph500, hnswlib, multichase | 3.0 | 3.0 | +1% to +3% | graph500 -1% | MERCI +16% | 4.16 | 1.00 |