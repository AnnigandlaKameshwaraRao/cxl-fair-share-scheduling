# Code

| Folder | What it holds |
| --- | --- |
| `simulator_patches/` | Every change made to CXL-ClusterSim (gem5 + the gem5–SST bridge + the run scripts), as diffs against upstream commit `43a51d2195fdce294851f0034c51f8053758d621` of [darchr/cxl-clustersim](https://github.com/darchr/cxl-clustersim), branch `stable`. `all_changes.patch` holds all of them; the other files are the same changes one file at a time. Doc 03 explains each change. |
| `btpmem/` | The SST element library with the scheduler front end, the seven host schedulers, FR-FCFS bank queues and the row-size-aware address mapper. Doc 12 describes the schedulers; doc 03 the components. |
| `workloads/` | Marker header, benchmark patches and per-workload run configurations, with build instructions in its README. |
| `run/` | Scripts to take checkpoints and run an experiment, and the container definition used on the cluster. |
| `experiments/` | The exact joblist of every run reported in the docs, grouped by stage. |

## simulator_patches

```bash
git clone https://github.com/darchr/cxl-clustersim.git ~/cxl-clustersim
cd ~/cxl-clustersim
git checkout 43a51d2195fdce294851f0034c51f8053758d621
git apply /path/to/code/simulator_patches/all_changes.patch
```

Then build gem5 and the gem5 library SST loads, as CXL-ClusterSim's README describes:

```bash
scons build/ALL/gem5.opt -j$(nproc)
scons build/ALL/libgem5_opt.so -j$(nproc) --without-tcmalloc --duplicate-sources
```

## btpmem

Needs SST-Core 14.0.0 installed (default prefix `~/sst-core`) and the SST-Elements 14.0.0 source tree (for memHierarchy's headers).

```bash
cd code/btpmem
make SST_PREFIX=$HOME/sst-core ELEM_SRC=/path/to/sst-elements-library-14.0.0/src
cp libbtpmem.so ~/cxl-clustersim/ext/sst/
```

`unified_sst.py` loads `btpmem` from `ext/sst` whenever a joblist asks for anything other than the stock pool (`pool-sched` other than `fcfs`, or a `pool-arb`).

| File | Content |
| --- | --- |
| `btpTimingDRAM.cc/.h` | Copy of memHierarchy's `timingDRAM` with `lazyPop`, the per-host front end (`arb`), per-host interference counters and the end-of-run command counts (`BTP_ROWSTATS`) |
| `btpArb.h` | State shared by the front end and the bank queues: host of an address, ranks, pending slots, served and interference counters |
| `btpSched.cc` | The host schedulers: `fcfs`, `frfcfs`, `static`, `bliss`, `atlas`, `tcm`, `parbs`, `saa`, with their settings and defaults |
| `frfcfsTransactionQ.cc` | Bank queue: host rank, then row hit, then age (PAR-BS: batch first) |
| `rowAddrMapper.cc` | Address mapper that honours the configured row size |

## run

| File | Use |
| --- | --- |
| `make_ckpt.sh <joblist> <slot> wl-<tag> [timeout-min]` | Boots one host under KVM from a `wl_<tag>_4slot.json` entry and saves its checkpoint to `ckpt_lib/wl-<tag>/btp_<slot>/checkpoint`. Needs KVM. Run once per workload and slot (48 checkpoints for the 12 workloads). |
| `run_experiment.sh <joblist> <tag>:<slot>` | Runs an alone experiment from a joblist in `experiments/`. |
| `run_experiment.sh <joblist> <tag0> <tag1> <tag2> <tag3>` | Runs a 4-host mix; host i restores the checkpoint of slot i. |
| `compose.py` | Builds a multi-host joblist and its checkpoint folder from the per-workload library (used for the early experiments). |
| `cxl-clustersim-runtime.def` | Apptainer definition with the runtime libraries; gem5 and SST are bound in from the host. |

Both shell scripts read the simulator path from `SIM` (default `~/cxl-clustersim`) and the SST binary from `SST` (default `~/sst-core/bin/sst`).

## experiments

One joblist per run, named as the run directory without its `_a1` suffix. Host 0's `metadata` holds the run-wide settings (`pool-channels`, `pool-sched`, `pool-row-size`, `pool-arb`, `pool-arb-params`, `max-ticks`, `stats-period-ms`) and a `comment` that says what the run is. Home paths are written as `~`.

| Folder | Runs |
| --- | --- |
| `1_phase1/p1w`, `p1s` | Phase 1 alone runs: slot 0 (`p1w`) and slots 1–3 (`p1s`), timing CPU, 400 ms |
| `1_phase1/p1m` | Phase 1 mixes 1–18 |
| `2_o3_baselines/o3a`, `o3c` | O3 alone runs, FCFS and FR-FCFS, 1 channel (`o3a`) and 2 channels (`o3c`) |
| `2_o3_baselines/o3b`, `o3d` | O3 mixes, FCFS and FR-FCFS, 1 channel (`o3b`) and 2 channels (`o3d`) |
| `2_o3_baselines/o3e`, `o3f` | L3 prefetcher off, 1 and 2 channels (doc 10) |
| `2_o3_baselines/o3t`, `o3u` | Short prefetcher-trace runs of STREAM (doc 10) |
| `3_scheduler_campaign/chk*`, `eq1`, `eq2` | Checks of the front end and of each scheduler, and the one-host equivalence runs (doc 14) |
| `3_scheduler_campaign/s1m` | 1-channel mixes: tuning variants on mixes 1, 4, 13 and the five schedulers on all mixes |
| `3_scheduler_campaign/s1a`, `s2a` | Campaign alone runs: PAR-BS on 1 channel; FCFS, FR-FCFS and PAR-BS on 2 channels |
| `3_scheduler_campaign/s2m` | 2-channel mixes: FCFS, FR-FCFS and the five schedulers |

Scheduler names in run names: `tcm`, `bliss`, `parbs`, `atlasr` (ATLAS, quantum 10M with the over-threshold rule), `saasm` (SAA, bandwidth estimate smoothed 0.75). Other names in `s1m` are the tuning variants of doc 13. The workload tags are: `v4tea` tealeaf, `v2stream24m` STREAM, `v5foton` fotonik3d, `v3sc` streamcluster, `v5roms` roms, `v2llamar5` LLM inference, `v2merci4` MERCI, `v5g500` graph500, `v2hnsw` hnswlib, `v5cactus` cactus, `v6mchase` multichase, `v5marian` Marian. `results/scheduler_campaign/mixdefs.txt` lists the four workloads of each mix in host order.
