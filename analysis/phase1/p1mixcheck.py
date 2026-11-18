from p1common import *
import re, statistics as st
NAMES = {'tealeaf': 'tealeaf', 'STREAM': 'STREAM', 'fotonik3d': 'fotonik3d', 'streamcluster': 'streamcluster', 'roms': 'roms', 'LLM inference': 'LLM inference', 'LLM': 'LLM inference',
         'MERCI': 'MERCI', 'mercI4': 'MERCI', 'merci4': 'MERCI', 'graph500': 'graph500', 'graph500 BFS': 'graph500', 'hnswlib': 'hnswlib', 'cactus': 'cactus', 'multichase': 'multichase', 'Marian': 'Marian'}
def wl(s): return NAMES[s.replace('\\*', '').replace('*', '').strip()]
lines = open('p1mixed.md').read().splitlines()
MIXW = {}
for l in lines:
    c = [x.strip() for x in l.strip('|').split('|')]
    if l.startswith('|') and len(c) == 8 and c[0].isdigit() and ('aggressor' in c[1] or 'victim' in c[1] or 'AI' in c[1]): MIXW[int(c[0])] = [wl(x) for x in c[2:6]]
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
def fair(C, d):
    n = len(d); alloc = [0.0] * n; left = C; act = list(range(n))
    while act and left > 1e-12:
        share = left / len(act); done = [i for i in act if d[i] - alloc[i] <= share]
        if not done:
            for i in act: alloc[i] += share
            break
        for i in done: left -= d[i] - alloc[i]; alloc[i] = d[i]
        act = [i for i in act if i not in done]
    return alloc
def mixm(k):
    ws = MIXW[k]; H = [m(h) for h in P[f'mix{k}']['hosts']]; A = [alone(w, i) for i, w in enumerate(ws)]
    prog = lambda x, w: x['rps'] if w in REQ else x['ips']
    sd = [prog(A[i], w) / prog(H[i], w) for i, w in enumerate(ws)]; nm = [i for i, w in enumerate(ws) if w != 'Marian']
    dem = [a['bw'] for a in A]; deliv = sum(h['bw'] for h in H); fs = fair(deliv, dem)
    wait = lambda x: max(x['lat'] - 245, 5)
    return dict(ws=ws, H=H, A=A, sd=sd, demand=sum(dem), deliv=deliv, latinc=[H[i]['lat'] / A[i]['lat'] - 1 for i in range(4)], ipsch=[H[i]['ips'] / A[i]['ips'] - 1 for i in range(4)],
                rpsch=[H[i]['rps'] / A[i]['rps'] - 1 for i in range(4)], wsp=sum(H[i]['ips'] / A[i]['ips'] for i in range(4)), jain_i=jain([H[i]['ips'] / A[i]['ips'] for i in range(4)]),
                jain_r=jain([H[i]['rps'] / A[i]['rps'] for i in range(4)]), jain_l=jain([A[i]['lat'] / H[i]['lat'] for i in range(4)]), jain_w=jain([wait(A[i]) / wait(H[i]) for i in range(4)]),
                jain_p95=jain([pct(A[i]['h'], .95) / pct(H[i]['h'], .95) for i in range(4)]), jain_bw=jain([H[i]['bw'] / fs[i] for i in range(4)]), fs=fs,
                maxi=max(nm, key=lambda i: sd[i]), mini=min(nm, key=lambda i: sd[i]))
res = {'ok': 0, 'round': [], 'bad': []}
def cmp(where, txt, val):
    t = txt.strip().replace('−', '-').replace('+', '').rstrip('%').replace(',', '')
    if not re.fullmatch(r'-?\d+(\.\d+)?', t): res['bad'].append(f'{where}: unparsed {txt!r}'); return
    dec = len(t.split('.')[1]) if '.' in t else 0; got, exp = float(t), round(val, dec)
    if got == exp: res['ok'] += 1
    elif abs(got - exp) <= 10 ** -dec * 1.01: res['round'].append(f'{where}: doc {txt} raw {val:.4f}')
    else: res['bad'].append(f'{where}: doc {txt} raw {val:.4f}')
M = {k: mixm(k) for k in MIXW}
for l in lines:
    c = [x.strip() for x in l.strip('|').split('|')]
    if not l.startswith('|') or not c[0].isdigit(): continue
    k = int(c[0]); x = M.get(k)
    if len(c) == 8 and k in MIXW and ('aggressor' in c[1] or 'victim' in c[1] or 'AI' in c[1]): cmp(f'mixlist {k} load', c[6], x['demand'])
    elif len(c) == 9 and ' to ' in c[4]:   # results per mix
        cmp(f'mix {k} demand', c[2], x['demand']); cmp(f'mix {k} deliv', c[3], x['deliv'])
        lo, hi = c[4].split(' to '); cmp(f'mix {k} latinc lo', lo, 100 * min(x['latinc'])); cmp(f'mix {k} latinc hi', hi, 100 * max(x['latinc']))
        for col, fn in ((5, min), (6, max)):
            name, v = c[col].rsplit(' ', 1); i = fn(range(4), key=lambda j: x['ipsch'][j])
            if wl(name) != x['ws'][i]: res['bad'].append(f'mix {k} col{col} host {name} vs {x["ws"][i]}')
            cmp(f'mix {k} col{col}', v, 100 * x['ipsch'][i])
        cmp(f'mix {k} WS', c[7], x['wsp']); cmp(f'mix {k} jain', c[8], x['jain_i'])
    elif len(c) == 9 and '→' in c[3]:   # every host
        h = int(c[1]); H, A = x['H'][h], x['A'][h]
        if wl(c[2]) != x['ws'][h]: res['bad'].append(f'host m{k} h{h} {c[2]} vs {x["ws"][h]}')
        for col, a, b in ((3, A['lat'], H['lat']), (5, A['ips'], H['ips']), (7, A['rps'], H['rps'])):
            u, v = c[col].split(' → '); cmp(f'host m{k} h{h} c{col}a', u, a); cmp(f'host m{k} h{h} c{col}b', v, b)
        cmp(f'host m{k} h{h} latinc', c[4], 100 * x['latinc'][h]); cmp(f'host m{k} h{h} ipsch', c[6], 100 * x['ipsch'][h]); cmp(f'host m{k} h{h} rpsch', c[8], 100 * x['rpsch'][h])
    elif len(c) == 13:   # fairness
        cmp(f'fair {k} demand', c[2], x['demand']); cmp(f'fair {k} deliv', c[3], x['deliv'])
        v, name = re.match(r'([\d.]+) \((.+)\)', c[4]).groups(); cmp(f'fair {k} max', v, x['sd'][x['maxi']])
        if wl(name) != x['ws'][x['maxi']]: res['bad'].append(f'fair {k} max host {name} vs {x["ws"][x["maxi"]]}')
        cmp(f'fair {k} min', c[5], x['sd'][x['mini']]); cmp(f'fair {k} unf', c[6], x['sd'][x['maxi']] / x['sd'][x['mini']])
        for col, key in zip(range(7, 13), ('jain_i', 'jain_r', 'jain_l', 'jain_w', 'jain_p95', 'jain_bw')): cmp(f'fair {k} {key}', c[col], x[key])
    elif len(c) == 8 and '→' in c[3] and c[1].isdigit():   # tail latency
        h = int(c[1]); H, A = x['H'][h]['h'], x['A'][h]['h']
        for col, q in ((3, .5), (4, .9), (5, .95), (6, .99)):
            u, v = c[col].split(' → ')
            for side, hh, t in (('a', A, u), ('m', H, v)):
                p = pct(hh, q)
                if t.startswith('>'):
                    if p != float('inf'): res['bad'].append(f'tail m{k} h{h} p{q} {side}: doc {t} raw {p}')
                    else: res['ok'] += 1
                else: cmp(f'tail m{k} h{h} p{q} {side}', t, p)
        tot = sum(H['hist'].values()) + H['over']; cmp(f'tail m{k} h{h} over2us', c[7], 100 * x['H'][h]['h']['over'] / tot)
print('cells OK', res['ok'], '| last-digit', len(res['round']), '| wrong', len(res['bad']))
for y in res['bad'][:60]: print('  BAD', y)
for y in res['round'][:40]: print('  ROUND', y)
