# Analysis scripts

Every number in the docs comes from the gem5 `stats.txt` of each host, the run's `config.json`, and the pool's command counts in the run log. The raw run folders total about 23 GB, so they are not in this repository. Instead, each stage has an extraction script that reduces every run folder to one JSON line (in `results/`), and table scripts that compute every reported value from those lines at full precision.

The table scripts run directly from this repository:

```bash
cd analysis/scheduler_campaign
python3 gen_mix.py        # all tables of docs 15 and 15b -> mix_tables.json in the current directory
python3 checkdoc.py       # compares every table in docs 15 and 15b with results/scheduler_campaign/mix_tables.json
python3 gen_camp.py       # tables of doc 14 -> camp_tables.json
python3 make_figures.py   # figures of doc 15 -> docs/figures/
cd ../o3_baselines
python3 make_figures.py   # figures of docs 10 and 11 -> docs/figures/
```

Each script finds its data in `results/<stage>/` (set `DATA` to use another folder). `gen_mix.py` and `gen_camp.py` reproduce `results/scheduler_campaign/mix_tables.json` and `camp_tables.json` exactly. `checkdoc.py` reports 25 of 26 generated tables matched cell for cell (4,390 cells). The one table it does not find, the per-test counts on the three tuning mixes, is not used in the docs.

The extraction scripts need the raw run folders: `python3 extract_mix.py <folder> ... > camp_mix.jsonl`.

## phase1 (docs 08 and 09)

| Script | What it does |
| --- | --- |
| `p1extract.py` | Reads every Phase 1 run's host statistics (requests, instructions, latency sum, latency histogram, dumps) into `p1raw.json` |
| `p1common.py` | Loads `results/phase1/p1raw.json`; per-workload, per-slot alone values; latency percentiles from the histogram |
| `p1alonecheck.py`, `p1mixcheck.py` | Recompute every number cell of the Phase 1 docs from `p1raw.json` and compare it with the doc text |
| `analyse2.py`, `three_measures.py` | The original Phase 1 analysis that wrote `results/phase1/*.csv`: per-host bandwidth, latency and progress per simulated second, each mix host against the alone run from the same slot, three measures kept separate |
| `win_series.py` | Pool bandwidth, latency and requests in flight of a run for each 10 ms statistics period |
| `tw_mean.py` | Time-weighted averages over a run |

## o3_baselines (docs 10 and 11)

| Script | What it does |
| --- | --- |
| `extract.py` | One JSON line per O3 run folder: per-host statistics, configuration, pool row-hit line |
| `o3data.py` | Loads `results/o3_baselines/local.jsonl` and `remote.jsonl`; alone values, mix metrics (slowdowns, highest slowdown, unfairness, weighted speedup, Jain's index, demand, delivered bandwidth, latency) with any alone baseline |
| `o3regen.py` | Rewrites every number cell of doc 11's tables from the raw data, keeping each row's labels and format |
| `o3check.py`, `o3alonecheck.py` | Recompute every number cell of docs 11 and 10 and compare it with the doc text |
| `make_figures.py` | The five figures of docs 10 and 11 |

## scheduler_campaign (docs 12 to 15)

| Script | What it does |
| --- | --- |
| `extract2.py`, `extract3.py` | One JSON line per alone run folder, with prefetch and miss counts and the pool's row statistics |
| `extract_mix.py` | One JSON line per mix run folder: per-host statistics, statistics dumps per host, `max_ticks` lines, pool row statistics, configuration |
| `campalone.py` | Alone baselines for every scheduler, channel count, workload and slot, with configuration checks |
| `mixdata.py` | Campaign mix data: one complete copy per run, every run's workloads, scheduler and settings checked against `mixdefs.txt`; `metrics(ch, sched, mix)` gives every measure of doc 15 |
| `gen_mix.py` | Every table of docs 15 and 15b |
| `gen_camp.py` | Every table of doc 14 |
| `checkdoc.py` | Cell-by-cell check of docs 15 and 15b against `mix_tables.json` |
| `eqcmp.py` | The one-host equivalence check of doc 14: compares two runs dump by dump, every gem5 statistic except host timing, and the pool statistics |
| `raw.py`, `check.py`, `gen.py`, `cells.py` | Tuning tables of docs 13 and 13b, recomputed independently from the raw statistics (need the raw run folders) |
| `make_figures.py` | The two figures of doc 15 |

## Definitions

- **Rates** are per simulated second over the covered statistics periods, so small differences in window length cancel.
- **Progress** is the instruction rate of a host's 4 cores. For MERCI and multichase it is the pool request rate, because their instruction counts include spin and wait loops.
- **Slowdown** = progress alone ÷ progress in the mix, for the same workload, checkpoint slot, scheduler and channel count (the alone baselines of each scheduler are listed in doc 15).
- **Highest slowdown** and **unfairness** (highest ÷ lowest slowdown) leave out Marian, which barely uses the pool.
- **Victim** = the host with the lowest alone pool bandwidth (1 channel, FR-FCFS), ignoring hosts under 0.1 GB/s.
- **Weighted speedup** = Σ progress ratios; **harmonic speedup** = 4 ÷ Σ slowdowns; **Jain's index** over the progress ratios.
- **Mix latency** (doc 15) is the bandwidth-weighted mean of the hosts' mean pool round trips, including the 250 ns link.
- **Row-hit rate** = 1 − activates ÷ column commands, from the pool's command counts.
