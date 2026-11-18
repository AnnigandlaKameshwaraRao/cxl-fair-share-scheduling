import json, os, re, statistics as st
DATA = os.environ.get('DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'results', 'o3_baselines'))
KW = [('streamcluster', 'streamcluster'), ('stream.hw', 'STREAM'), ('tealeaf', 'tealeaf'), ('fotonik3d', 'fotonik3d'), ('roms', 'roms'), ('merci', 'MERCI'),
      ('multichase', 'multichase'), ('graph500', 'graph500'), ('cactus', 'cactus'), ('marian-decoder', 'Marian'), ('hnsw', 'hnswlib'), ('llama-bench', 'LLM inference')]
TAG = {'tealeaf': 'v4tea', 'STREAM': 'v2stream24m', 'fotonik3d': 'v5foton', 'roms': 'v5roms', 'MERCI': 'v2merci4', 'streamcluster': 'v3sc', 'multichase': 'v6mchase',
       'graph500': 'v5g500', 'cactus': 'v5cactus', 'Marian': 'v5marian', 'hnswlib': 'v2hnsw', 'LLM inference': 'v2llamar5'}
R = {}
for f in ('local2.jsonl', 'remote2.jsonl'):
    for l in open(os.path.join(DATA, f)):
        r = json.loads(l); R.setdefault(r['name'], r)
problems = []
def run(wave, s, w, k, ch):
    r = R.get(f'{wave}_{s}_{TAG[w]}_s{k}')
    if r is None: problems.append(f'missing {wave} {s} {w} s{k}'); return None
    c = json.loads(r['cmds'][0]); cmd = json.dumps(c.get('workload', c))
    if str(r['channels']) != str(ch) or r['sched'] != s or not any(k2 in cmd for k2, n in KW if n == w): problems.append(f"{r['name']}: config {r['channels']} {r['sched']}")
    h = r['hosts'][0]
    return dict(bw=h['reqs'] * 64 / h['secs'] / 1e9, lat=h['latsum'] / h['reqs'] / 1000, ips=h['insts'] / h['secs'] / 1e9, rh=float(r['rowhit']) if r['rowhit'] else None,
                pf=h['pf'] * 1000 / h['insts'], mm=h['mshrmiss'] * 1000 / h['insts'], secs=h['secs'])
wave = {1: 'o3a', 2: 'o3c'}
A = {(s, w, k, ch): run(wave[ch], s, w, k, ch) for s in ('fcfs', 'frfcfs') for w in TAG for k in range(4) for ch in (1, 2)}
OFF = {(s, w): run('o3e', s, w, 2, 1) for s in ('fcfs', 'frfcfs') for w in ('tealeaf', 'STREAM', 'fotonik3d', 'streamcluster', 'roms', 'MERCI', 'graph500', 'cactus')}
def mean(s, w, ch, key): return st.mean(A[(s, w, k, ch)][key] for k in range(4))
res = {'ok': 0, 'round': [], 'bad': []}
def cmp(where, txt, val):
    t = txt.strip().replace('−', '-').replace('+', '').rstrip('%')
    dec = len(t.split('.')[1]) if '.' in t else 0; got, exp = float(t), round(val, dec)
    if got == exp: res['ok'] += 1
    elif abs(got - exp) <= 10 ** -dec * 1.01: res['round'].append(f'{where}: doc {txt} raw {val:.4f}')
    else: res['bad'].append(f'{where}: doc {txt} raw {val:.4f}')
lines = open('o3alone.md').read().splitlines(); i = 0; sub = ''
while i < len(lines):
    l = lines[i]
    if l.startswith('### '): sub = l[4:]
    if l.startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
        hdr = [c.strip() for c in l.strip('|').split('|')]; i += 2; rows = []
        while i < len(lines) and lines[i].startswith('|'): rows.append([c.strip() for c in lines[i].strip('|').split('|')]); i += 1
        if hdr[0] == 'Workload' and hdr[-1] == 'Row-hit rate FR-FCFS':
            ch = 1 if sub == 'One channel' else 2; off = 2 if ch == 1 else 1
            for r in rows:
                w = r[0]; c = r[off:]
                for j, (s, key) in enumerate([('fcfs', 'bw'), ('frfcfs', 'bw'), ('fcfs', 'lat'), ('frfcfs', 'lat'), ('fcfs', 'ips'), ('frfcfs', 'ips'), ('frfcfs', 'rh')]):
                    cmp(f'{ch}ch {w} {hdr[off + j]}', c[j], mean(s, w, ch, key))
        elif hdr[0] == 'Workload' and hdr[1].startswith('1 channel: instr'):
            for r in rows:
                w = r[0]
                for ci, ch, kind in ((1, 1, 'chg'), (2, 1, 'rh'), (3, 2, 'chg'), (4, 2, 'rh')):
                    for k, t in enumerate(r[ci].split(' / ')):
                        v = 100 * (A[('frfcfs', w, k, ch)]['ips'] / A[('fcfs', w, k, ch)]['ips'] - 1) if kind == 'chg' else A[('frfcfs', w, k, ch)]['rh']
                        cmp(f'slot {w} {ch}ch {kind} s{k}', t, v)
        elif hdr[0] == 'Workload' and hdr[1].startswith('Prefetches'):
            for r in rows:
                w = r[0]
                for j, (s, ch, key) in enumerate([('fcfs', 1, 'pf'), ('frfcfs', 1, 'pf'), ('fcfs', 2, 'pf'), ('frfcfs', 2, 'pf'), ('fcfs', 1, 'mm'), ('frfcfs', 1, 'mm')]):
                    cmp(f'pf {w} {hdr[j + 1]}', r[j + 1], mean(s, w, ch, key))
        elif hdr[0] == 'Slot 2':
            for r in rows:
                w = r[0]; key = 'bw' if r[1].startswith('pool') else 'ips'
                on = {s: A[(s, w, 2, 1)][key] for s in ('fcfs', 'frfcfs')}; off = {s: OFF[(s, w)][key] for s in ('fcfs', 'frfcfs')}
                for j, v in enumerate([on['frfcfs'] / on['fcfs'] - 1, off['frfcfs'] / off['fcfs'] - 1, on['fcfs'] / off['fcfs'] - 1, on['frfcfs'] / off['frfcfs'] - 1]):
                    cmp(f'pfoff {w} {hdr[j + 2]}', r[j + 2], 100 * v)
        continue
    i += 1
print('cells OK', res['ok'], '| last-digit', len(res['round']), '| wrong', len(res['bad'])); print('problems', problems)
for x in res['bad']: print('  BAD', x)
for x in res['round']: print('  ROUND', x)
