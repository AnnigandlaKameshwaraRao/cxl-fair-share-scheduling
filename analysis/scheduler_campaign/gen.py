import sys, json
sys.argv = ['x']; exec(open('check.py').read().replace("print('problems:'", "_=('problems:'").replace("print('mix workloads:'", "_=('mix workloads:'"))
MIXES = ('m04', 'm13', 'm01')
PER = ['FCFS', 'FR-FCFS', 'ATLAS 10M', 'ATLAS 10M + rule', 'ATLAS 1M', 'ATLAS 1M + rule', 'TCM', 'BLISS', 'PAR-BS', 'SAA', 'SAA, smoothing']
def B(doc, s): return 'fcfs' if (doc == 'fcfs' or s == 'FCFS') else 'frfcfs'
def mean(doc, s, k): return sum(metrics(s, m, B(doc, s))[k] for m in MIXES) / 3
def f2(x): return f'{x:.2f}'
def f3(x): return f'{x:.3f}'
def bolded(rows, cols):  # cols: (key, fmt, sense)
    best = {}
    for k, fmt, sense in cols:
        vals = [fmt(v[k]) for _, v in rows]
        best[k] = (min if sense < 0 else max)(vals, key=float)
    return best
out = {}
for doc in ('frfcfs', 'fcfs'):
    keys = [('max', f2, -1), ('unf', f2, -1), ('ws', f2, 1)]
    if doc == 'fcfs': keys += [('mean', f2, -1), ('cv', f2, -1), ('jp', f3, 1), ('jbs', f3, 1), ('bsu', f2, -1), ('jbw', f3, 1), ('hs', f3, 1), ('gbs', lambda x: f'{x:.1f}', 1)]
    rows = sorted([(s, {k: mean(doc, s, k) for k, _, _ in keys}) for s in PER], key=lambda r: r[1]['max'])
    best = bolded(rows, keys)
    if doc == 'frfcfs': hdr = '| Scheduler | Mean largest slowdown | Mean unfairness | Mean weighted speedup |'
    else: hdr = '| Scheduler | Mean largest slowdown | Mean unfairness | Mean weighted speedup | Mean slowdown | Mean spread (CV) | Mean Jain, progress | Mean Jain, bandwidth share | Mean bandwidth-share unfairness | Mean Jain, raw bandwidth | Mean harmonic speedup | Mean delivered (GB/s) |'
    t = hdr + '\n|' + ' --- |' * (len(keys) + 1) + '\n'
    for s, v in rows:
        lab = 'SAA, smoothing 0.75' if s == 'SAA, smoothing' else s
        t += f'| {lab} | ' + ' | '.join((f'**{fmt(v[k])}**' if fmt(v[k]) == best[k] else fmt(v[k])) for k, fmt, _ in keys) + ' |\n'
    out[f'{doc}_summary'] = t.strip()
    # per-mix
    for m in MIXES:
        cols = [('unf', f2), ('ws', f2)]
        names = ['Unfairness', 'Weighted speedup']
        if doc == 'fcfs':
            cols += [('mean', f2), ('cv', f2), ('jp', f3), ('jbs', f3), ('bsu', f2), ('jbw', f3), ('hs', f3), ('gbs', lambda x: f'{x:.1f}')]
            names += ['Mean slowdown', 'Spread (CV)', 'Jain, progress', 'Jain, bandwidth share', 'Bandwidth-share unfairness', 'Jain, raw bandwidth', 'Harmonic speedup', 'Delivered (GB/s)']
        t = '| Scheduler | ' + ' | '.join(WL[m]) + ' | ' + ' | '.join(names) + ' |\n|' + ' --- |' * (5 + len(cols)) + '\n'
        for s in PER:
            v = metrics(s, m, B(doc, s))
            t += f'| {s} | ' + ' | '.join(f2(x) for x in v['sd']) + ' | ' + ' | '.join(fmt(v[k]) for k, fmt in cols) + ' |\n'
        out[f'{doc}_{m}'] = t.strip()
    # chart rows
    out[f'{doc}_chart'] = {s: [round(metrics(s, m, B(doc, s))['max'], 2) for m in MIXES] for s in PER if s != 'FCFS'}
    # ATLAS / SAA variant tables
    var = ['ATLAS 10M', 'ATLAS 10M + rule', 'ATLAS 1M', 'ATLAS 1M + rule'] + (['SAA', 'SAA, smoothing'] if doc == 'fcfs' else [])
    t = ('| ATLAS variant |' if doc == 'frfcfs' else '| Variant |') + ' Largest m04 | Largest m13 | Largest m01 | Mean largest | Mean unfairness | Mean weighted speedup |\n|' + ' --- |' * 7 + '\n'
    for s in var:
        lab = s.replace('ATLAS ', '') if doc == 'frfcfs' else ('SAA, smoothing 0.75' if s == 'SAA, smoothing' else s)
        t += f'| {lab} | ' + ' | '.join(f2(metrics(s, m, B(doc, s))['max']) for m in MIXES) + f" | {f2(mean(doc, s, 'max'))} | {f2(mean(doc, s, 'unf'))} | {f2(mean(doc, s, 'ws'))} |\n"
    out[f'{doc}_variants'] = t.strip()
    if doc == 'frfcfs':
        t = '| Mix | Largest: SAA | Largest: smoothing | Unfairness: SAA | Unfairness: smoothing | Weighted speedup: SAA | Weighted speedup: smoothing | Host 3: SAA | Host 3: smoothing |\n|' + ' --- |' * 9 + '\n'
        lab = {'m04': 'm04 (victim MERCI)', 'm13': 'm13 (host 3 streamcluster)', 'm01': 'm01 (victim multichase)'}
        for m in MIXES:
            a, b = metrics('SAA', m, 'frfcfs'), metrics('SAA, smoothing', m, 'frfcfs')
            cells = []
            for k in ('max', 'unf'):
                x, y = f2(a[k]), f2(b[k]); lo = min(x, y, key=float)
                cells += [f'**{x}**' if x == lo and x != y else x, f'**{y}**' if y == lo and x != y else y]
            cells += [f2(a['ws']), f2(b['ws']), f2(a['sd'][3]), f2(b['sd'][3])]
            t += f'| {lab[m]} | ' + ' | '.join(cells) + ' |\n'
        out['frfcfs_saa'] = t.strip()
json.dump(out, open('gen.json', 'w'), indent=1)
print(out['frfcfs_summary']); print(out['fcfs_summary']); print(json.dumps(out['frfcfs_chart'])); print(json.dumps(out['fcfs_chart']))
