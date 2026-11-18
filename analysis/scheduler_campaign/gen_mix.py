"""All tables of the mix report, from mixdata (raw stats). Writes mix_tables.json: markdown per table + raw values."""
import json, statistics as st
import mixdata as M
L = M.LABEL; S = M.SCHED
HO = [m for m in range(1, 19) if m not in M.TUNE]; TU = list(M.TUNE); ALL = list(range(1, 19))
SHORT = {'tealeaf': 'tealeaf', 'STREAM': 'STREAM', 'fotonik3d': 'fotonik3d', 'streamcluster': 'streamcluster', 'roms': 'roms',
         'LLM inference': 'LLM', 'MERCI': 'MERCI', 'graph500': 'graph500', 'hnswlib': 'hnswlib', 'cactus': 'cactus',
         'multichase': 'multichase', 'Marian': 'Marian'}
def f(v, d):
    s = f'{v:.{d}f}'
    return s
def mean(xs): return st.mean(xs)
def table(hdr, rows): return '| ' + ' | '.join(hdr) + ' |\n| ' + ' | '.join('---' for _ in hdr) + ' |\n' + '\n'.join('| ' + ' | '.join(r) + ' |' for r in rows)
def bold_best(cols, vals, dec, better):  # vals: list per row (None allowed) -> formatted with best bolded
    shown = [f(v, dec) if v is not None else '–' for v in vals]
    nums = [round(v, dec) for v in vals if v is not None]
    if not nums: return shown
    b = min(nums) if better == 'low' else max(nums)
    return [f'**{s}**' if v is not None and round(v, dec) == b else s for s, v in zip(shown, vals)]
OUT = {}; RAW = {}
def summary(ch, ms, key):
    base_fr = 'o1fr' if ch == 1 else 'n2fr'
    X = {s: [M.metrics(ch, s, m) for m in ms] for s in S}
    C = {s: [M.metrics(ch, s, m, base_fr) for m in ms] for s in S}
    cols = [('max', 2, 'low', X), ('vic', 2, 'low', X), ('unf', 2, 'low', X), ('ws', 2, 'high', X), ('hs', 3, 'high', X), ('jain', 3, 'high', X),
            ('deliv', 1, 'high', X), ('lat', 0, 'low', X), ('rowhit', 2, None, X), ('max', 2, 'low', C), ('vic', 2, 'low', C)]
    vals = []
    for k, d, b, src in cols:
        v = []
        for s in S:
            xs = [x[k] for x in src[s] if x[k] is not None]
            v.append(mean(xs) if xs and len(xs) == len(ms) else None)
        vals.append((v, d, b))
    RAW[key] = {s: [vals[i][0][j] for i in range(len(cols))] for j, s in enumerate(S)}
    fm = [bold_best(None, v, d, b) if b else [f(x, d) if x is not None else '–' for x in v] for v, d, b in vals]
    hdr = ['Scheduler', 'Highest slowdown', 'Victim slowdown', 'Unfairness', 'Weighted speedup', 'Harmonic speedup', "Jain's index",
           'Delivered (GB/s)', 'Mean latency (ns)', 'Row-hit rate', 'Highest slowdown, FR-FCFS alone runs', 'Victim slowdown, FR-FCFS alone runs']
    rows = [[L[s]] + [fm[i][j] for i in range(len(cols))] for j, s in enumerate(S)]
    OUT[key] = table(hdr, rows)
def tests(ch, ms, key):
    rows = []; raw = {}
    for s in S[2:] + ['fcfs']:
        a = b = c = 0; worst = []
        for m in ms:
            x = M.metrics(ch, s, m); fr = M.metrics(ch, 'frfcfs', m)
            a += x['max'] < fr['max']; b += x['vic'] > fr['vic']; c += x['ws'] < fr['ws']
        raw[s] = (a, b, c)
        rows.append([L[s], f'{a} of {len(ms)}', f'{b} of {len(ms)}', f'{c} of {len(ms)}'])
    RAW[key] = raw
    OUT[key] = table(['Scheduler', 'Highest slowdown below FR-FCFS', 'Victim slowdown above FR-FCFS', 'Weighted speedup below FR-FCFS'], rows)
summary(1, HO, 't1_sum'); summary(1, TU, 't1_tune'); summary(2, ALL, 't2_sum')
tests(1, HO, 't1_tests'); tests(1, TU, 't1_tune_tests'); tests(2, ALL, 't2_tests')
# mixes table
rows = []
for m in ALL:
    ws = M.MIXW[m]
    grp = '3 aggressors + 1 victim' if m <= 6 else '2 + 2' if m <= 12 else '4 aggressors' if m <= 14 else '1 aggressor + 3 victims' if m <= 16 else 'all AI' if m == 17 else '4 victims'
    dem = sum(M.CA.A[('o1fr', w, k)]['bw'] for k, w in enumerate(ws))
    rows.append([str(m) + (' (tuning)' if m in TU else ''), *[SHORT[w] for w in ws], grp, SHORT[ws[M.VICTIM[m]]], f(dem, 1)])
OUT['t_mix'] = table(['Mix', 'Host 0', 'Host 1', 'Host 2', 'Host 3', 'Group', 'Victim', 'Demand alone (GB/s)'], rows)
# 1 vs 2 channels, all 18 mixes
rows = []; RAW['t12'] = {}
for s in S:
    a = [M.metrics(1, s, m) for m in ALL]; b = [M.metrics(2, s, m) for m in ALL]
    c1 = [M.metrics(1, s, m, 'o1fr') for m in ALL]; c2 = [M.metrics(2, s, m, 'o1fr') for m in ALL]
    v = [mean(x['max'] for x in a), mean(x['max'] for x in b), mean(x['max'] for x in c1), mean(x['max'] for x in c2),
         mean(x['vic'] for x in c1), mean(x['vic'] for x in c2), mean(x['deliv'] for x in a), mean(x['deliv'] for x in b)]
    RAW['t12'][s] = v
    rows.append([L[s], f(v[0], 2), f(v[1], 2), f(v[2], 2), f(v[3], 2), f(v[4], 2), f(v[5], 2), f(v[6], 1), f(v[7], 1)])
OUT['t12'] = table(['Scheduler', 'Highest slowdown, 1 ch', 'Highest slowdown, 2 ch', 'Highest slowdown vs 1-ch FR-FCFS alone, 1 ch',
                    'Highest slowdown vs 1-ch FR-FCFS alone, 2 ch', 'Victim slowdown vs 1-ch FR-FCFS alone, 1 ch', 'Victim slowdown vs 1-ch FR-FCFS alone, 2 ch',
                    'Delivered (GB/s), 1 ch', 'Delivered (GB/s), 2 ch'], rows)
# per mix tables
def permix(ch, k, d, better, key, host=False):
    rows = []; raw = {}
    for m in ALL:
        xs = [M.metrics(ch, s, m) for s in S]; v = [x[k] for x in xs]; raw[m] = v
        cells = bold_best(None, v, d, better) if better else [f(x, d) if x is not None else '–' for x in v]
        if host: cells = [f'{c} ({SHORT[x["maxw"]]})' for c, x in zip(cells, xs)]
        rows.append([str(m) + (' (tuning)' if ch == 1 and m in TU else '')] + cells)
    RAW[key] = raw
    OUT[key] = table(['Mix'] + [L[s] for s in S], rows)
for ch in (1, 2):
    permix(ch, 'max', 2, 'low', f'pm{ch}_max', host=True); permix(ch, 'vic', 2, 'low', f'pm{ch}_vic'); permix(ch, 'unf', 2, 'low', f'pm{ch}_unf')
    permix(ch, 'ws', 2, 'high', f'pm{ch}_ws'); permix(ch, 'deliv', 1, 'high', f'pm{ch}_deliv'); permix(ch, 'lat', 0, 'low', f'pm{ch}_lat')
    permix(ch, 'rowhit', 2, None, f'pm{ch}_rh')
# per host tables
for ch in (1, 2):
    rows = []; raw = {}
    for m in ALL:
        xs = [M.metrics(ch, s, m) for s in S]
        for k, w in enumerate(M.MIXW[m]):
            v = [x['sd'][k] for x in xs]; raw[f'{m}_{k}'] = v
            tag = SHORT[w] + ('*' if w in M.REQ else '') + (' (victim)' if k == M.VICTIM[m] else '')
            rows.append([str(m), str(k), tag] + [f(x, 2) for x in v])
    RAW[f'ph{ch}'] = raw
    OUT[f'ph{ch}'] = table(['Mix', 'Host', 'Workload'] + [L[s] for s in S], rows)
# per workload: mean slowdown over the mixes it is in
WL = ['tealeaf', 'STREAM', 'fotonik3d', 'roms', 'streamcluster', 'LLM inference', 'graph500', 'MERCI', 'cactus', 'hnswlib', 'multichase', 'Marian']
for ch, ms, key in ((1, HO, 'wl1'), (2, ALL, 'wl2')):
    rows = []; raw = {}
    for w in WL:
        occ = [(m, k) for m in ms for k, ww in enumerate(M.MIXW[m]) if ww == w]
        v = [mean(M.metrics(ch, s, m)['sd'][k] for m, k in occ) for s in S]; raw[w] = (len(occ), v)
        rows.append([SHORT[w] + ('*' if w in M.REQ else ''), str(len(occ))] + bold_best(None, v, 2, 'low'))
    RAW[key] = raw
    OUT[key] = table(['Workload', 'Mixes', *[L[s] for s in S]], rows)
json.dump({'md': OUT, 'raw': RAW}, open('mix_tables.json', 'w'), indent=1)
for k, v in OUT.items():
    if k in ('t1_sum', 't1_tests', 't2_sum', 't2_tests', 't12', 't1_tune', 'wl1', 'wl2', 't_mix'): print('##', k); print(v); print()
