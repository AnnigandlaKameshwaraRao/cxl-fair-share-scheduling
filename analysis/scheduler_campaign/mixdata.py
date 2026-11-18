"""Campaign mix data: one complete copy per run, configs checked, per-host rates at full precision."""
import json, collections, os, statistics as st
D = os.path.dirname(os.path.abspath(__file__))
cwd = os.getcwd(); os.chdir(D)
import campalone as CA          # alone runs: CA.A[(set, workload, slot)] -> bw, lat, ips, rh
os.chdir(cwd)
DATA = CA.DATA
NAME = {v: k for k, v in CA.TAG.items()}
MIXW = {}
for l in open(os.path.join(DATA, 'mixdefs.txt')):
    n, _, w = l.split(); MIXW[int(n[-2:])] = [NAME[x] for x in w.split(',')]
SCHED = ['fcfs', 'frfcfs', 'tcm', 'atlasr', 'bliss', 'parbs', 'saasm']
LABEL = {'fcfs': 'FCFS', 'frfcfs': 'FR-FCFS', 'tcm': 'TCM', 'atlasr': 'ATLAS', 'bliss': 'BLISS', 'parbs': 'PAR-BS', 'saasm': 'SAA'}
ARB = {'fcfs': 'fcfs', 'frfcfs': 'frfcfs', 'tcm': 'tcm', 'atlasr': 'atlas', 'bliss': 'bliss', 'parbs': 'parbs', 'saasm': 'saa'}
PARAMS = {'atlasr': {'quantum': 10000000, 'threshold': 100000}, 'saasm': {'estimate': 'bandwidth', 'smooth': 0.75}}
BASESET = {(1, 'fcfs'): 'o1fc', (2, 'fcfs'): 'n2fc', (1, 'parbs'): 'p1', (2, 'parbs'): 'p2'}
def baseset(ch, s): return BASESET.get((ch, s), 'o1fr' if ch == 1 else 'n2fr')
REQ = {'MERCI', 'multichase'}
TUNE = (1, 4, 13)
problems = []
R = {}
for l in open(os.path.join(DATA, 'camp_mix.jsonl')):
    r = json.loads(l)
    if not (len(r['dumps']) == 4 and min(r['dumps']) >= 10 and (r['maxticks_lines'] or 0) >= 4 and all(r['hosts'])): continue
    if r['name'] in R: problems.append('two complete copies ' + r['name'])
    R[r['name']] = r
def rname(ch, s, m):
    if ch == 1 and s in ('fcfs', 'frfcfs'): return f'o3b_{s}_m{m:02d}'
    return f's{ch}m_{s}_m{m:02d}'
MIX = {}
for ch in (1, 2):
    for s in SCHED:
        for m in range(1, 19):
            n = rname(ch, s, m); r = R.get(n)
            if r is None: problems.append('missing ' + n); continue
            wl = [next(w for w, k in CA.KW.items() if k in c) for c in r['cmds']]
            if wl != MIXW[m]: problems.append(f'{n}: workloads {wl}')
            want_sched = 'fcfs-copy' if (ch == 2 and s == 'fcfs') else ('fcfs' if s == 'fcfs' else 'frfcfs')
            want_arb = None if (ch == 1 and s in ('fcfs', 'frfcfs')) else ARB[s]
            if str(r['channels']) != str(ch) or r['sched'] != want_sched or r['arb'] != want_arb or r['maxticks'] != '300000000':
                problems.append(f"{n}: config ch={r['channels']} sched={r['sched']} arb={r['arb']} maxticks={r['maxticks']}")
            if s in PARAMS and r['params'] != PARAMS[s]: problems.append(f"{n}: params {r['params']}")
            if s not in PARAMS and r['params'] is not None: problems.append(f"{n}: params {r['params']}")
            H = []
            for h in r['hosts']:
                H.append(dict(bw=h['reqs'] * 64 / h['secs'] / 1e9, ips=h['insts'] / h['secs'] / 1e9, lat=h['latsum'] / h['reqs'] / 1000,
                              rps=h['reqs'] / h['secs'], secs=h['secs'], reqs=h['reqs']))
            rs = r['rowstats'][-1] if r['rowstats'] else None
            MIX[(ch, s, m)] = dict(name=n, dir=r['dir'], wl=wl, H=H, rowhit=(1 - rs[1] / rs[2]) if rs else None, rowstats=rs, nrows=len(r['rowstats'] or []))
def prog(h, w): return h['bw'] if w in REQ else h['ips']
VICTIM = {}
for m, ws in MIXW.items():   # lowest alone pool bandwidth, 1 channel FR-FCFS, ignoring hosts under 0.1 GB/s
    c = [(CA.A[('o1fr', w, k)]['bw'], k) for k, w in enumerate(ws) if CA.A[('o1fr', w, k)]['bw'] >= 0.1]
    VICTIM[m] = min(c)[1]
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
def metrics(ch, s, m, bset=None):
    x = MIX[(ch, s, m)]; ws = x['wl']; H = x['H']; bset = bset or baseset(ch, s)
    A = [CA.A[(bset, w, k)] for k, w in enumerate(ws)]
    sd = [prog(A[k], w) / prog(H[k], w) for k, w in enumerate(ws)]
    nm = [k for k, w in enumerate(ws) if w != 'Marian']
    mx = max(nm, key=lambda k: sd[k]); mn = min(nm, key=lambda k: sd[k])
    pr = [1 / v for v in sd]
    return dict(sd=sd, max=sd[mx], maxw=ws[mx], maxk=mx, min=sd[mn], unf=sd[mx] / sd[mn], vic=sd[VICTIM[m]], vicw=ws[VICTIM[m]],
                ws=sum(pr), hs=len(sd) / sum(sd), jain=jain(pr), deliv=sum(h['bw'] for h in H),
                lat=sum(h['lat'] * h['bw'] for h in H) / sum(h['bw'] for h in H), rowhit=x['rowhit'],
                demand=sum(A[k]['bw'] for k in range(4)), hosts=H, alone=A)
if __name__ == '__main__':
    print('problems:', problems or 'none', '| alone problems:', CA.problems or 'none')
    print('runs', len(MIX), 'victims', {m: MIXW[m][k] for m, k in VICTIM.items()})
    print('rowstats lines per run', collections.Counter(x['nrows'] for x in MIX.values()))
    # pool column commands vs requests seen at the hosts' bridges
    for k in [(1, 'frfcfs', 4), (2, 'frfcfs', 4), (2, 'fcfs', 4), (1, 'saasm', 13)]:
        x = MIX[k]; print(k, 'COL', x['rowstats'][2] if x['rowstats'] else None, 'host reqs', sum(h['reqs'] for h in x['H']))
