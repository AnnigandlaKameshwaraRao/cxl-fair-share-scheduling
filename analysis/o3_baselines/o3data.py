import json, os, statistics as st
DATA = os.environ.get('DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'results', 'o3_baselines'))
KW = [('streamcluster', 'streamcluster'), ('stream.hw', 'STREAM'), ('tealeaf', 'tealeaf'), ('fotonik3d', 'fotonik3d'), ('roms', 'roms'),
      ('merci', 'MERCI'), ('multichase', 'multichase'), ('graph500', 'graph500'), ('cactus', 'cactus'), ('marian-decoder', 'Marian'),
      ('hnsw', 'hnswlib'), ('llama-bench', 'LLM inference')]
REQ = {'MERCI', 'multichase'}
def wl(cfgtxt):
    def cmds(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'cmd': yield json.dumps(v)
                else: yield from cmds(v)
    c = ' '.join(cmds(json.loads(cfgtxt)))
    for k, n in KW:
        if k in c: return n
R, dups = {}, []
for f in ('local.jsonl', 'remote.jsonl'):
    for l in open(os.path.join(DATA, f)):
        r = json.loads(l)
        if r['name'] in R:
            a, b = R[r['name']]['hosts'], r['hosts']
            if any(abs(x['insts'] - y['insts']) > 0 or abs(x['reqs'] - y['reqs']) > 0 for x, y in zip(a, b)): dups.append(r['name'])
            continue
        r['wl'] = [wl(c) for c in r['cmds']]
        for h in r['hosts']:
            h['bw'] = h['reqs'] * 64 / h['secs'] / 1e9; h['ips'] = h['insts'] / h['secs'] / 1e9; h['lat'] = h['latsum'] / h['reqs'] / 1000 if h['reqs'] else 0
        R[r['name']] = r
def prog(h, w): return h['bw'] if w in REQ else h['ips']
problems = []
def mix(m, sch, ch):
    r = R[f"{'o3b' if ch == 1 else 'o3d'}_{sch}_m{m:02d}"]
    if str(r['channels']) != str(ch) or r['sched'] != sch: problems.append(f"{r['name']}: ch {r['channels']} sched {r['sched']}")
    return r
TAG = {'tealeaf': 'v4tea', 'STREAM': 'v2stream24m', 'fotonik3d': 'v5foton', 'roms': 'v5roms', 'MERCI': 'v2merci4', 'streamcluster': 'v3sc',
       'multichase': 'v6mchase', 'graph500': 'v5g500', 'cactus': 'v5cactus', 'Marian': 'v5marian', 'hnswlib': 'v2hnsw', 'LLM inference': 'v2llamar5'}
def alone(sch, w, slot, ch):
    waves = ('o3a', 'o3e') if ch == 1 else ('o3c',)
    for wv in waves:
        r = R.get(f'{wv}_{sch}_{TAG[w]}_s{slot}')
        if r:
            if str(r['channels']) != str(ch) or r['sched'] != sch or r['wl'][0] != w: problems.append(f"{r['name']}: bad config {r['channels']} {r['sched']} {r['wl']}")
            return r['hosts'][0]
    problems.append(f'missing alone {sch} {w} s{slot} {ch}ch'); return None
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
def mixmetrics(m, sch, ch, base_sch=None, base_ch=None):
    r = mix(m, sch, ch); base_sch = base_sch or sch; base_ch = base_ch or ch
    ws = r['wl']; H = r['hosts']
    A = [alone(base_sch, w, i, base_ch) for i, w in enumerate(ws)]
    sd = [prog(A[i], w) / prog(H[i], w) for i, w in enumerate(ws)]
    nm = [i for i, w in enumerate(ws) if w != 'Marian']
    mx = max(nm, key=lambda i: sd[i])
    ir = [H[i]['ips'] / A[i]['ips'] for i in range(4)]
    dem = sum(alone('fcfs', w, i, ch)['bw'] for i, w in enumerate(ws))
    return dict(ws=ws, sd=sd, max=sd[mx], maxw=ws[mx], unf=sd[mx] / min(sd[i] for i in nm), wsp=sum(ir), jain=jain(ir), demand=dem,
                deliv=sum(h['bw'] for h in H), lat=sum(h['latsum'] for h in H) / sum(h['reqs'] for h in H) / 1000, latbw=sum(h['lat'] * h['bw'] for h in H) / sum(h['bw'] for h in H), rowhit=r['rowhit'], hosts=H)
