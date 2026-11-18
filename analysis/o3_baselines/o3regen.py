"""Rewrite every number cell of the O3 mixed doc's tables from raw data, keeping each row's labels, order and format."""
import re, json, statistics as st
from o3data import *
lines = open('o3mixed.md').read().splitlines()
def fmt_like(txt, val):
    t = txt.strip(); sign = t.startswith(('+', '−', '-')); pct = t.endswith('%')
    core = t.lstrip('+−-').rstrip('%'); dec = len(core.split('.')[1]) if '.' in core else 0
    s = f'{abs(val):.{dec}f}'
    if pct:
        if round(val, dec) == 0: return f'0{"." + "0" * dec if dec else ""}%'
        return ('+' if val > 0 else '−') + s + '%'
    return ('−' + s) if val < 0 else s
def arrow(cell, a, b):
    x, y = [c.strip() for c in cell.split('→')]; return f'{fmt_like(x, a)} → {fmt_like(y, b)}'
new = list(lines); changed = []; i = 0; sub = ''; tables = []
while i < len(lines):
    l = lines[i]
    if l.startswith('### ') or re.fullmatch(r'\*\*(One|Two) channels?\*\*', l): sub = l.strip('#* ')
    if l.startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
        hdr = [c.strip() for c in l.strip('|').split('|')]; start = i; i += 2
        while i < len(lines) and lines[i].startswith('|'):
            r = [c.strip() for c in lines[i].strip('|').split('|')]; o = list(r)
            if hdr[0] == 'Mix' and hdr[1].startswith('Workloads'):
                ch = 1 if sub == 'One channel' else 2; m = int(r[0]); f, g = mixmetrics(m, 'fcfs', ch), mixmetrics(m, 'frfcfs', ch)
                o[2] = fmt_like(r[2], f['demand']); o[3] = arrow(r[3], f['deliv'], g['deliv']); o[4] = arrow(r[4], f['latbw'], g['latbw'])
                o[5] = f"{fmt_like(r[5].split()[0], f['max'])} ({f['maxw']})"; o[6] = f"{fmt_like(r[6].split()[0], g['max'])} ({g['maxw']})"
                o[7] = arrow(r[7], f['unf'], g['unf']); o[8] = arrow(r[8], f['wsp'], g['wsp']); o[9] = arrow(r[9], f['jain'], g['jain']); o[10] = fmt_like(r[10], float(g['rowhit']))
            elif hdr[0] == 'Mix' and hdr[1] == 'Host':
                ch = 1 if 'one channel' in sub else 2; m, h = int(r[0]), int(r[1]); f, g = mixmetrics(m, 'fcfs', ch), mixmetrics(m, 'frfcfs', ch); x = mixmetrics(m, 'frfcfs', ch, 'fcfs', ch)
                o[3] = arrow(r[3], f['hosts'][h]['bw'], g['hosts'][h]['bw']); o[4] = arrow(r[4], f['hosts'][h]['lat'], g['hosts'][h]['lat'])
                o[5] = arrow(r[5], f['hosts'][h]['ips'], g['hosts'][h]['ips']); o[6] = arrow(r[6], f['sd'][h], g['sd'][h]); o[7] = fmt_like(r[7], x['sd'][h])
            elif hdr[0] == 'Workload' and hdr[1] == 'Measure':
                ch = 1 if sub.startswith('One') else 2; w = r[0].replace('\\*', '').replace('*', '')
                occ = [(m, k) for m in range(1, 19) for k, ww in enumerate(mix(m, 'fcfs', ch)['wl']) if ww == w]
                pa = lambda s: [prog(alone(s, w, k, ch), w) for m, k in occ]; pm = lambda s: [prog(mix(m, s, ch)['hosts'][k], w) for m, k in occ]
                af, ar, mf, mr = pa('fcfs'), pa('frfcfs'), pm('fcfs'), pm('frfcfs')
                o[2] = str(len(occ)); o[3] = fmt_like(r[3], st.mean(af)); o[4] = fmt_like(r[4], st.mean(ar)); o[5] = fmt_like(r[5], 100 * st.mean(b / a - 1 for a, b in zip(af, ar)))
                o[6] = fmt_like(r[6], st.mean(mf)); o[7] = fmt_like(r[7], st.mean(mr)); o[8] = fmt_like(r[8], 100 * st.mean(b / a - 1 for a, b in zip(mf, mr)))
            elif hdr[0] == 'Across the 18 mixes':
                for c, (s, ch) in enumerate([('fcfs', 1), ('frfcfs', 1), ('fcfs', 2), ('frfcfs', 2)], start=2):
                    M = [mixmetrics(m, s, ch) for m in range(1, 19)]
                    key = {'Delivered (GB/s)': 'deliv', 'Max slowdown': 'max', 'Unfairness': 'unf', "Jain's index (instructions)": 'jain'}.get(r[0])
                    vals = [x[key] for x in M] if key else [sum(alone(s, w, k, ch)['bw'] for k, w in enumerate(x['ws'])) for x in M]
                    lo, hi = r[c].split('–'); o[c] = f'{fmt_like(lo, min(vals))}–{fmt_like(hi, max(vals))}'
            nl = '| ' + ' | '.join(o) + ' |'
            if nl != lines[i]: changed.append((hdr[0] + '/' + (hdr[1] if len(hdr) > 1 else ''), sub, lines[i], nl)); new[i] = nl
            i += 1
        tables.append((start, i)); continue
    i += 1
json.dump({'new': new, 'changed': changed, 'tables': tables}, open('o3regen.json', 'w'))
print(len(changed), 'rows change')
for t, s, a, b in changed:
    ca = [c.strip() for c in a.strip('|').split('|')]; cb = [c.strip() for c in b.strip('|').split('|')]
    print(f'[{s}] {ca[0]} {ca[1] if t.startswith("Mix/Host") else ""}:', '; '.join(f'{x} -> {y}' for x, y in zip(ca, cb) if x != y))
