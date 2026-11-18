import json, os, statistics as st, sys
DATA = os.environ.get('DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'results', 'scheduler_campaign'))
TAG = {'tealeaf': 'v4tea', 'STREAM': 'v2stream24m', 'fotonik3d': 'v5foton', 'streamcluster': 'v3sc', 'roms': 'v5roms', 'LLM inference': 'v2llamar5',
       'MERCI': 'v2merci4', 'graph500': 'v5g500', 'hnswlib': 'v2hnsw', 'cactus': 'v5cactus', 'multichase': 'v6mchase', 'Marian': 'v5marian'}
KW = {'tealeaf': 'tealeaf', 'STREAM': 'stream.hw', 'fotonik3d': 'fotonik3d', 'streamcluster': 'streamcluster', 'roms': 'roms', 'LLM inference': 'llama-bench',
      'MERCI': 'merci', 'graph500': 'graph500', 'hnswlib': 'hnsw', 'cactus': 'cactus', 'multichase': 'multichase', 'Marian': 'marian-decoder'}
O3DATA = os.path.join(DATA, '..', 'o3_baselines')   # O3 alone runs: the 1-channel FCFS and FR-FCFS baselines
R = {}
for f in (os.path.join(O3DATA, 'local2.jsonl'), os.path.join(O3DATA, 'remote2.jsonl'), os.path.join(DATA, 'camp_alone.jsonl')):
    for l in open(f):
        r = json.loads(l); R.setdefault(r['name'], r)
problems = []
# set -> (prefix, channels, sched, arb)
SETS = {'o1fc': ('o3a_fcfs', '1', 'fcfs', None), 'o1fr': ('o3a_frfcfs', '1', 'frfcfs', None),
        'o2fc': ('o3c_fcfs', '2', 'fcfs', None), 'o2fr': ('o3c_frfcfs', '2', 'frfcfs', None),
        'p1': ('s1a_parbs', '1', 'frfcfs', 'parbs'), 'n2fc': ('s2a_fcfs', '2', 'fcfs-copy', 'fcfs'),
        'n2fr': ('s2a_frfcfs', '2', 'frfcfs', 'frfcfs'), 'p2': ('s2a_parbs', '2', 'frfcfs', 'parbs')}
def run(s, w, k):
    pre, ch, sch, arb = SETS[s]; r = R.get(f'{pre}_{TAG[w]}_s{k}')
    if r is None: problems.append(f'missing {s} {w} {k}'); return None
    c = r['cmds'][0]
    if str(r['channels']) != ch or r['sched'] != sch or r.get('arb') != arb or KW[w] not in c: problems.append(f"{r['name']}: config {r['channels']} {r['sched']} {r.get('arb')}")
    h = r['hosts'][0]
    return dict(bw=h['reqs'] * 64 / h['secs'] / 1e9, lat=h['latsum'] / h['reqs'] / 1000, ips=h['insts'] / h['secs'] / 1e9,
                rh=float(r['rowhit']) if r['rowhit'] else None, pf=h['pf'] * 1000 / h['insts'], mm=h['mshrmiss'] * 1000 / h['insts'], secs=h['secs'])
A = {(s, w, k): run(s, w, k) for s in SETS for w in TAG for k in range(4)}
def mean(s, w, key): return st.mean(A[(s, w, k)][key] for k in range(4))
def chg(a, b, w, key='ips'): return st.mean(A[(a, w, k)][key] / A[(b, w, k)][key] - 1 for k in range(4))  # mean of per-slot ratios
if __name__ == '__main__':
    print('problems', problems)
    for w in TAG:
        print(f"{w:14s}", ' '.join(f"{s}:{mean(s,w,'ips'):.3f}/{mean(s,w,'bw'):.2f}/{mean(s,w,'lat'):.0f}/{mean(s,w,'rh') if A[(s,w,0)]['rh'] is not None else float('nan'):.2f}" for s in SETS))
