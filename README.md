# Fair-Share Scheduling at a Multi-Host CXL Memory Pool

With CXL memory pooling, several servers (hosts) share one memory device. When the device serves requests first come, first served, a host that keeps many requests in flight takes most of the bandwidth, and a light, latency-bound host waits behind it and slows down far more than its share of the traffic would suggest. This project studies that unfairness in simulation and evaluates schedulers that run **inside the pool device**: they reorder requests using only what the device can see (each request's host, address and the DRAM bank state), with no change to or cooperation from the hosts.

The work was done on CXL-ClusterSim (gem5 hosts joined to an SST memory pool) with four 4-core hosts, twelve standard workloads (four of them AI workloads) and eighteen four-host mixes.

## Main results

- **First come, first served is unfair at saturation.** On a saturated pool, a pointer-chasing host that sends about 2% of the traffic slows 1.49×, as much as or more than the streaming hosts that cause the congestion (doc 05). Identical hosts, by contrast, are treated equally (doc 06).
- **Realistic mixes show the same pattern.** In the 18 Phase 1 mixes the pool delivers at most 11.5 GB/s of its 19.2 GB/s peak, light latency-bound hosts lose the most (graph500 loses 61% of its instruction rate in mix 2), and Jain's index stays at 0.93 or above, hiding the gap (doc 09).
- **FR-FCFS raises throughput but not fairness.** With out-of-order cores, FR-FCFS raises what one channel delivers from at most 12.2 GB/s to 14.7–16.8 GB/s in the heavy mixes, but its worst host still slows 1.67–4.33× (doc 11).
- **Device-side schedulers help on one channel at no throughput cost.** Over the 15 held-out mixes on one channel, against FR-FCFS: the mean highest slowdown falls from 1.77 to 1.57–1.70; ATLAS keeps the victim at 1.20 against 1.55; SAA, this project's scheduler, has the lowest unfairness (1.30) and the highest Jain's index (0.982); and weighted speedup rises from 2.96 to 3.05–3.16 (doc 15).
- **A second channel matters more than the scheduler.** On two channels all schedulers end within a few percent of FR-FCFS, and FR-FCFS's mean highest slowdown on the shared baseline falls from 2.08 on one channel to 1.36 (doc 15).

## Reading order

The docs are numbered in the order the work was done. Each one says what was asked, how it was measured and what was found.

| Doc | Stage | What it answers |
| --- | --- | --- |
| [01](docs/01_related_work_and_positioning.md) | Related work | What CXL's own QoS does, what devices publish, why round robin is not enough, and what is new here |
| [02](docs/02_fairness_metrics.md) | Metrics | Which quantities to measure, where each comes from, and two simulator fixes they needed |
| [03](docs/03_simulator_setup.md) | Simulator | Every change made to the simulator, the bugs fixed, and the configuration of each stage |
| [04](docs/04_simulated_pool_vs_real_devices.md) | Simulator | How the simulated pool compares with real multi-headed CXL devices, and where the scheduler sits |
| [05](docs/05_saturating_the_pool.md) | Evidence | Does a light host lose out when the pool saturates under FCFS? |
| [06](docs/06_host_scaling.md) | Evidence | Is contention real when all hosts are the same, and is FCFS fair between equal hosts? |
| [07](docs/07_workloads.md) | Workloads | The 12 workloads, why each was chosen, and the candidates dropped |
| [08](docs/08_phase1_alone.md) | Phase 1 | What each workload needs from the pool on its own |
| [09](docs/09_phase1_mixed.md) | Phase 1 | How unfair the pool is in 18 realistic mixes |
| [10](docs/10_o3_alone.md) | Baselines | Out-of-order cores alone: FCFS against FR-FCFS, one channel against two |
| [11](docs/11_o3_mixed.md) | Baselines | The 18 mixes under FCFS and FR-FCFS on one and two channels |
| [12](docs/12_scheduler_design.md) | Design | The scheduler front end, how each of the seven schedulers works, SAA, settings, cost on a real device |
| [13](docs/13_scheduler_tuning.md), [13b](docs/13b_tuning_fcfs_baseline.md) | Tuning | Settings chosen on three heavy mixes, against FR-FCFS and against FCFS alone runs |
| [14](docs/14_campaign_alone.md) | Campaign | Alone runs: the new front end with one host, PAR-BS alone, equivalence checks |
| [15](docs/15_campaign_mix_results.md), [15b](docs/15b_campaign_per_mix_data.md) | Campaign | The final comparison of all schedulers over the 18 mixes on one and two channels |

## Repository layout

```
docs/       write-ups 01-15 and their figures
code/       simulator patches, the scheduler (SST element), workload patches, run scripts,
            and the joblist of every run                      -> code/README.md
analysis/   extraction, table and figure scripts               -> analysis/README.md
results/    compact per-run data behind every table            -> results/README.md
```

## Reproducing the work

The numbers in the docs can be checked in minutes from the included data. Rerunning the simulations needs the full toolchain and, for the mixes, a machine with about 24 GB of memory per mix.

### 1. Check the tables and figures from the included data

```bash
pip install matplotlib
cd analysis/scheduler_campaign
python3 gen_mix.py && python3 checkdoc.py    # rebuilds every table of docs 15/15b and compares cell by cell
python3 gen_camp.py                          # tables of doc 14
python3 make_figures.py                      # figures of doc 15
cd ../o3_baselines && python3 make_figures.py   # figures of docs 10 and 11
```

### 2. Build the simulator

On an x86-64 Linux machine (Ubuntu 24.04 was used) with KVM, Python 3, SCons, Open MPI and gem5's build dependencies (`code/run/cxl-clustersim-runtime.def` lists the packages):

1. Install [SST-Core 14.0.0](https://github.com/sstsimulator/sst-core) and [SST-Elements 14.0.0](https://github.com/sstsimulator/sst-elements) (for example to `~/sst-core`).
2. Clone [CXL-ClusterSim](https://github.com/darchr/cxl-clustersim) to `~/BTP/cxl-clustersim`, check out commit `43a51d2195fdce294851f0034c51f8053758d621`, apply `code/simulator_patches/all_changes.patch`, and build `build/ALL/gem5.opt` and `build/ALL/libgem5_opt.so` (commands in `code/README.md`).
3. In `ext/sst`, link the SST binary and the SST-Elements libraries, as doc 03 describes ("Build and setup problems").
4. Build the scheduler element in `code/btpmem` and copy `libbtpmem.so` to `ext/sst`.

### 3. Build the guest

1. Clone [gem5-resources](https://github.com/kaustav-goswami/gem5-resources), branch `disaggregated`, into the simulator folder.
2. Build Linux 6.9.9 with its `config.x86.6.9.9` configuration.
3. Build its Ubuntu 24.04 x86 disk image, apply the fixes in doc 03, and add the workloads as `code/workloads/README.md` describes. The six SPEC CPU 2026 workloads need your own SPEC licence; the other six are open source.

The joblists expect the kernel at `~/BTP/linux-kernel-build/linux/vmlinux` and the images under `~/BTP/cxl-clustersim/gem5-resources/src/stream/x86-disk-image-24-04/`; edit the `kernel` and `disk` fields if yours are elsewhere.

### 4. Take checkpoints and run

```bash
export SIM=~/BTP/cxl-clustersim
# one checkpoint per workload and host slot (12 workloads x 4 slots), booted under KVM
for s in 0 1 2 3; do code/run/make_ckpt.sh code/workloads/joblists/wl_v4tea_4slot.json $s wl-v4tea 40; done
# an alone run: tealeaf from slot 2, one channel, FR-FCFS, O3 cores
code/run/run_experiment.sh code/experiments/2_o3_baselines/o3a/exp_o3a_frfcfs_v4tea_s2.json v4tea:2
# a mix: mix 4 under SAA on two channels (host order from results/scheduler_campaign/mixdefs.txt)
code/run/run_experiment.sh code/experiments/3_scheduler_campaign/s2m/exp_s2m_saasm_m04.json v4tea v5foton v5roms v2merci4
```

An alone run of 100 ms takes from tens of minutes to a few hours on one desktop core; a 4-host mix takes several hours to a day. Every run writes `btp_<host>/stats.txt` with one block per 10 ms, and its log holds the pool's command counts.

### 5. Analyse

Reduce the run folders with the extraction scripts (`analysis/README.md`), then run the table scripts on the new JSON lines.

## Copyright and licence

Copyright © 2026 Annigandla Kameshwara Rao.

- **Code** (`code/`, `analysis/`): BSD 3-Clause, see `LICENSE`. The simulator patches are changes to gem5/CXL-ClusterSim and fall under its BSD 3-Clause licence; files derived from SST-Elements keep NTESS's notice.
- **Documentation and data** (`docs/`, `results/`): Creative Commons Attribution 4.0 (CC BY 4.0), see `LICENSE-docs`.
- **Third-party software** stays under its own licence; `THIRD_PARTY.md` lists each project and what of it, if anything, is in this repository. SPEC CPU 2026 material is not included.

If you use this work, please cite this repository and credit the author.
