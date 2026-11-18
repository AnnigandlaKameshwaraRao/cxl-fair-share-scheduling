# Simulator Setup

All experiments run on CXL-ClusterSim, which joins two simulators. Several bugs had to be fixed before it could run multi-host experiments reliably, and a few features were added. This document lists every change, why it was needed, and the configuration used in each stage. The changes are in `code/simulator_patches/` as diffs against the upstream commit in `base_commit.txt`.

## What the simulator is

- **gem5** models each host: x86 cores, caches, local DRAM and a full Linux system.
- **SST** models the shared CXL memory pool: memHierarchy's memory controller and a DDR DRAM model (`timingDRAM`).

Each host is a separate gem5 process, and the processes run in lockstep with SST under MPI. Every request a host sends to the pool crosses a modelled CXL link (a fixed 250 ns) into SST. Inside the guest the pool appears as a NUMA node with no CPUs, which is how Linux shows CXL memory, and workloads are placed on it with `numactl --membind=1`.

In the stock simulator the pool's memory controller serves requests through one first-come-first-served front queue, with FIFO queues per DRAM bank and no fairness policy. That is where the scheduler of doc 12 goes.

SimCXL, a single-node gem5 CXL simulator, was set up first as a cross-check. Its LMbench run gave about 35 ns per CXL access, below the 170–250 ns of real devices because it models no link or switch. It cannot model several hosts, so it was used only to confirm the toolchain.

## Configuration in each stage

| Part | Saturation and host-scaling studies (docs 05, 06) | Phase 1 (docs 08, 09) | O3 baselines and scheduler campaign (docs 10–15) |
| --- | --- | --- | --- |
| Hosts | 1–4, with 1, 2 or 4 cores | 1 or 4, with 4 cores | 1 or 4, with 4 cores |
| CPU in the measured region | gem5 timing CPU (in-order, one demand miss per core) | timing CPU | gem5 O3 CPU (out-of-order) |
| Boot and setup | KVM, then a checkpoint | KVM, then a checkpoint per host slot | the same checkpoints as Phase 1 |
| Caches per host | 32 KiB L1d and L1i, 512 KiB L2 per core, 8 MiB shared L3, stride prefetchers; MSHRs 20 at L2 and L3, raised in one set of runs | as before; MSHRs L1d 16, L2 48, L3 192; write buffers L2 32, L3 64 | as Phase 1 |
| Local memory | DDR4, 1 GiB (2 GiB in the first single-host runs) | 1 GiB DDR4 | 1 GiB DDR4 |
| Pool slice per host | 1 GiB above 4 GiB | 1 GiB above 4 GiB | 1 GiB above 4 GiB |
| CXL link | 250 ns fixed | 250 ns fixed | 250 ns fixed |
| Pool channels | 1 or 2 DDR4-2400, 19.2 GB/s each | 1 | 1 or 2 |
| Bank queues and rows | FIFO, closed page; 16 KiB effective rows | FIFO, closed page; 16 KiB rows | FCFS (FIFO, closed page) or FR-FCFS (open page); 8 KiB rows |
| Measurement | each benchmark's marked regions | fixed 400 ms window, statistics every 10 ms | fixed 100 ms window, statistics every 10 ms |
| Scheduler front end | stock | stock | stock (O3 baselines); per-host front end (campaign) |
| Guest | Ubuntu 24.04, Linux 6.9.9 built from source | as before | as before |

How to read this table: one column per stage, in the order the work was done. A later stage changes only what its column shows.

## Changes to gem5 and the gem5–SST bridge

| File | Change | Why |
| --- | --- | --- |
| `src/dev/mc146818.cc` | Clamp the real-time-clock event offsets saved in a checkpoint to at least 1 tick. | The offset was computed with unsigned arithmetic. It underflowed to about 2^64 when an event was due exactly at the checkpoint tick, and the restore then crashed (`when >= getCurTick()` assertion). Before the fix, 15 of 15 attempts crashed. |
| `src/arch/x86/kvm/x86_cpu.cc` | Copy the boot-CPU bit of the APIC base register into KVM. | Linux 6.9 and later used only one CPU when that bit was missing. |
| `disaggregated_memory/boards/x86_main_board.py` | Add an ACPI entry for every core, and boot the guest with `idle=halt`. | Without the ACPI entry only the boot core came up. The timing CPU mishandles MWAIT in the idle loop: an idle core page-faulted and panicked. |
| `disaggregated_memory/cachehierarchies/dm_caches.py`, `configs/x86_unified.py` | Make MSHRs and write buffers per cache configurable per run; make the L3 prefetcher selectable (`stride` or `none`). | The defaults (20 at L2 and L3) capped how hard a 4-core host could press the pool, well below a real server. Turning the prefetcher off separates its effect from the pool's. |
| `configs/x86_unified.py` | New option `stats-period-ms`: dump and reset statistics every N simulated ms. | To see each host's pool traffic over time and to cut a fixed window out of every run. |
| `disaggregated_memory/unified_run.py`, `ext/sst/gem5.cc` | Fix the `max-ticks` limit. The run script read `jobs[0]` where the keys are strings, and the bridge checked the limit only on gem5 exit events; it now checks every cycle. | Needed to stop every run after a fixed window in the middle of a workload. |
| `src/sst/external_memory.cc/.hh`, `ext/sst/sst_responder_subcomponent.cc` | Free write-back packets and their tracking entries; give the latency histogram 5 ns buckets from 0 to 2 µs. | Every write-back sent to the pool leaked memory, so memory use grew for the whole run (runs before and after the fix are bit-identical in every simulated statistic). The histogram gives per-host latency percentiles (doc 02). |
| `ext/sst/sst/unified_sst.py` | Pool channel count, bank-queue policy (`pool-sched`), DRAM row size (`pool-row-size`) and the scheduler front end (`pool-arb`, `pool-arb-level`, `pool-arb-params`) set per run from the joblist. | Lets one simulator build run every configuration of the study; the scheduler options load the `btpmem` SST element from `code/btpmem`. |

## The scheduler element (`code/btpmem`)

`btpmem` is an SST element library built against SST-Elements 14.0.0. It holds three components:

- **`btpmem.timingDRAM`**: a copy of memHierarchy's `timingDRAM` with two additions. `lazyPop` lets a bank take its next request only when its command queue is empty, so the bank-queue policy decides at issue time. `arb` adds the per-host front end: a queue per host and channel, a channel arbiter filling each channel's 32 pending slots, and a host ranking set by a scheduler (FCFS, FR-FCFS, static, BLISS, ATLAS, TCM, PAR-BS or SAA; `btpSched.cc`). It also prints the pool's activate, precharge and column-command counts at the end of a run (`BTP_ROWSTATS`), from which row-hit rates are computed.
- **`btpmem.frfcfsTransactionQ`**: bank queues that pick by host rank, then row hit, then age (PAR-BS: batch first).
- **`btpmem.rowAddrMapper`**: an address mapper that honours the configured row size. The stock mapper ignores it and keeps 256 consecutive lines (16 KiB) of a channel in one row.

With `pool-sched = fcfs-copy` the element runs the stock FIFO, closed-page bank logic. A check run of this copy matches the stock code in every statistic. It is used where FCFS needs the front end or row counts.

## Build and setup problems fixed outside the code

| Problem | Fix |
| --- | --- |
| The kernel extracted from the distribution image was empty (0 bytes); the old extract script failed silently. | Built Linux 6.9.9 from source with the configuration shipped in gem5-resources (`config.x86.6.9.9`). |
| STREAM and the gem5 guest tool were missing from the disk image: the image build's `git clone` steps failed without stopping the build. | Built them separately and copied them into the image. The guest tool needs root ownership and setuid to reach `/dev/mem`. |
| Boot stalled on a segfaulting network configuration step. | Moved the netplan files aside and masked the wait-online service in the image. |
| The run script ignored the `--sst` path and loaded SST element libraries from a hard-coded directory. | Symbolic links to the installed SST binary and libraries in `ext/sst`. |
| Pool ranges below 4 GiB collided with x86's I/O hole ("two ports responding"). | Placed every host's 1 GiB pool slice above 4 GiB, as in the CXL-ClusterSim paper. |
| Open MPI bound every 2-rank alone run to the same CPUs, so parallel runs shared two physical cores and ran about 8× slower. | Set the binding policy to none (`OMPI_MCA_hwloc_base_binding_policy=none`) and pinned each run to its own cores. |
| The simulated CPU reports only SSE3/SSSE3, so binaries built for the build machine crashed. | Built every workload for plain `x86-64` (doc 07 and `code/workloads/README.md`). |

## Where the runs were done

Runs were spread over a lab desktop (Intel Core i7-12700, 15 GB RAM plus swap), a university SLURM cluster (CPU-only use of its nodes, inside an Apptainer container built from `code/run/cxl-clustersim-runtime.def`) and, for part of the campaign, other lab desktops. A machine claimed the next run from a shared queue and returned its result folder. The simulator is deterministic: the same joblist and checkpoint give the same statistics, and repeated runs matched exactly (doc 14). Simulation speed depends on single-core speed, so one run took several times longer on the cluster nodes than on the desktop.

A 4-host O3 mix needs about 24 GB of memory for 100 ms of simulated time; an alone run about 6 GB.
