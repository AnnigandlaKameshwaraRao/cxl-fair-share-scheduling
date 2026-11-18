import re, statistics as st
from o3data import *
lines = open('o3mixed.md').read().splitlines()
res = {'ok': 0, 'round': [], 'bad': []}
def cmp(where, txt, val):
    txt = txt.strip().replace('−', '-').replace('+', '').rstrip('%')
    if not re.fullmatch(r'-?\d+(\.\d+)?', txt): res['bad'].append(f'{where}: unparsed {txt!r}'); return
    dec = len(txt.split('.')[1]) if '.' in txt else 0
    got, exp = float(txt), round(val, dec)
    if got == exp: res['ok'] += 1
    elif abs(got - exp) <= 10 ** -dec * 1.01: res['round'].append(f'{where}: doc {txt} raw {val:.4f}')
    else: res['bad'].append(f'{where}: doc {txt} raw {val:.4f}')
def arrow(where, cell, a, b):
    x, y = [c.strip() for c in cell.split('→')]; cmp(where + ' FCFS', x, a); cmp(where + ' FR', y, b)
def tables():
    i, sec, sub = 0, '', ''
    while i < len(lines):
        l = lines[i]
        if l.startswith('## '): sec = l[3:]; sub = ''
        if l.startswith('### ') or re.fullmatch(r'\*\*(One|Two) channels?\*\*', l): sub = l.strip('#* ')
        if l.startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
            hdr = [c.strip() for c in l.strip('|').split('|')]; rows = []; i += 2
            while i < len(lines) and lines[i].startswith('|'): rows.append([c.strip() for c in lines[i].strip('|').split('|')]); i += 1
            yield sec, sub, hdr, rows; continue
        i += 1
for sec, sub, hdr, rows in tables():
    if hdr[0] == 'Mix' and hdr[1].startswith('Workloads'):
        ch = 1 if sub == 'One channel' else 2
        for r in rows:
            m = int(r[0]); f, g = mixmetrics(m, 'fcfs', ch), mixmetrics(m, 'frfcfs', ch); w = f'{ch}ch mix {m}'
            if ', '.join(f['ws']) != r[1]: res['bad'].append(f'{w}: workloads {r[1]} vs {f["ws"]}')
            cmp(w + ' demand', r[2], f['demand']); arrow(w + ' delivered', r[3], f['deliv'], g['deliv']); arrow(w + ' latency', r[4], f['latbw'], g['latbw'])
            for col, x in ((5, f), (6, g)):
                v, host = re.match(r'([\d.]+) \((.+)\)', r[col]).groups(); cmp(f'{w} max col{col}', v, x['max'])
                if host != x['maxw']: res['bad'].append(f'{w} max host col{col}: doc {host} raw {x["maxw"]}')
            arrow(w + ' unf', r[7], f['unf'], g['unf']); arrow(w + ' WS', r[8], f['wsp'], g['wsp']); arrow(w + ' jain', r[9], f['jain'], g['jain'])
            cmp(w + ' rowhit', r[10], float(g['rowhit']))
    elif hdr[0] == 'Mix' and hdr[1] == 'Host':
        ch = 1 if 'one channel' in sub else 2
        for r in rows:
            m, h = int(r[0]), int(r[1]); f, g = mixmetrics(m, 'fcfs', ch), mixmetrics(m, 'frfcfs', ch); x = mixmetrics(m, 'frfcfs', ch, 'fcfs', ch)
            w = f'{ch}ch host m{m} h{h}'
            if r[2].replace('\\*', '').replace('*', '') != f['ws'][h]: res['bad'].append(f'{w}: workload {r[2]} vs {f["ws"][h]}')
            arrow(w + ' bw', r[3], f['hosts'][h]['bw'], g['hosts'][h]['bw']); arrow(w + ' lat', r[4], f['hosts'][h]['lat'], g['hosts'][h]['lat'])
            arrow(w + ' ips', r[5], f['hosts'][h]['ips'], g['hosts'][h]['ips']); arrow(w + ' sd', r[6], f['sd'][h], g['sd'][h]); cmp(w + ' sd vs fcfs alone', r[7], x['sd'][h])
    elif hdr[0] == 'Workload' and hdr[1] == 'Measure':
        ch = 1 if sub.startswith('One') else 2
        for r in rows:
            w = r[0].replace('\\*', '').replace('*', ''); occ = [(m, i) for m in range(1, 19) for i, ww in enumerate(mix(m, 'fcfs', ch)['wl']) if ww == w]
            pa = lambda s: [prog(alone(s, w, i, ch), w) for m, i in occ]; pm = lambda s: [prog(mix(m, s, ch)['hosts'][i], w) for m, i in occ]
            af, ar, mf, mr = pa('fcfs'), pa('frfcfs'), pm('fcfs'), pm('frfcfs'); tag = f'{ch}ch wl {w}'
            cmp(tag + ' mixes', r[2], len(occ)); cmp(tag + ' alone fcfs', r[3], st.mean(af)); cmp(tag + ' alone fr', r[4], st.mean(ar))
            cmp(tag + ' gain alone', r[5], 100 * st.mean(b / a - 1 for a, b in zip(af, ar))); cmp(tag + ' mix fcfs', r[6], st.mean(mf)); cmp(tag + ' mix fr', r[7], st.mean(mr))
            cmp(tag + ' gain mix', r[8], 100 * st.mean(b / a - 1 for a, b in zip(mf, mr)))
    elif hdr[0] == 'Across the 18 mixes':
        sets = [('fcfs', 1), ('frfcfs', 1), ('fcfs', 2), ('frfcfs', 2)]
        for r in rows:
            for col, (s, ch) in zip(r[2:], sets):
                M = [mixmetrics(m, s, ch) for m in range(1, 19)]
                key = {'Demand alone (GB/s)': None, 'Delivered (GB/s)': 'deliv', 'Max slowdown': 'max', 'Unfairness': 'unf', "Jain's index (instructions)": 'jain'}[r[0]]
                if key: vals = [x[key] for x in M]
                else: vals = [sum(alone(s, w, i, ch)['bw'] for i, w in enumerate(x['ws'])) for x in M]
                lo, hi = col.split('–'); cmp(f'range {r[0]} {s} {ch}ch lo', lo, min(vals)); cmp(f'range {r[0]} {s} {ch}ch hi', hi, max(vals))
print('cells OK', res['ok'], '| off by one in last digit', len(res['round']), '| wrong', len(res['bad']))
print('problems', problems)
for x in res['bad']: print('  BAD', x)
for x in res['round']: print('  ROUND', x)
