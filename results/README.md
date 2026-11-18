# Results

Compact per-run data from which every table and figure in the docs is computed (see `analysis/README.md`). Each JSON line holds one run: its name, its run folder name, its configuration, and per host the simulated seconds, pool requests, committed instructions, summed pool latency, prefetch and miss counts, and statistics dumps. Rows also carry the pool's activate, precharge and column-command counts where the run printed them. Home paths are written as `~`.

| File | Runs | Used by |
| --- | --- | --- |
| `phase1/p1raw.json` | 66 Phase 1 runs (48 alone runs over 4 slots, 18 mixes) and earlier variants, timing CPU, 400 ms | docs 08 and 09 |
| `phase1/01_alone_runs_by_slot.csv` | The 48 Phase 1 alone runs: window, pool bandwidth and latency, instruction and request rates | doc 08 |
| `phase1/02_mixes_summary.csv` | The 18 Phase 1 mixes: demand, delivered bandwidth, latency and progress changes, weighted speedup, Jain's index | doc 09 |
| `phase1/03_mix_hosts.csv` | The 72 Phase 1 mix hosts, three measures each against the same-slot alone run | doc 09 |
| `phase1/04_mix_table.md`, `04b_every_host_table.md` | The two main tables of doc 09 | doc 09 |
| `o3_baselines/local.jsonl`, `remote.jsonl` | O3 alone and mix runs, FCFS and FR-FCFS, 1 and 2 channels, 100 ms, split by where the run folders were read (lab desktop or cluster); `o3data.py` checks that a run present in both is identical | docs 10 and 11 |
| `o3_baselines/local2.jsonl`, `remote2.jsonl` | O3 alone runs re-extracted with prefetch, miss and row counts; also the 1-channel alone baselines of the campaign | docs 10 and 14 |
| `scheduler_campaign/camp_alone.jsonl` | Campaign alone runs (2-channel FCFS and FR-FCFS, PAR-BS on 1 and 2 channels) and the equivalence checks | doc 14 |
| `scheduler_campaign/camp_mix.jsonl` | Every mix run folder of the O3 and campaign mixes, including empty copies; `mixdata.py` keeps one complete copy per run | docs 13 and 15 |
| `scheduler_campaign/mixdefs.txt` | The four workloads of each of the 18 mixes, host 0 first | docs 9 to 15 |
| `scheduler_campaign/mix_tables.json` | Every table of docs 15 and 15b, as markdown and raw values (output of `gen_mix.py`) | doc 15 |
| `scheduler_campaign/camp_tables.json` | Every table of doc 14 (output of `gen_camp.py`) | doc 14 |

The raw gem5 and SST outputs (`stats.txt`, `config.ini`, `config.json`, logs; about 23 GB for all runs) are kept off this repository.
