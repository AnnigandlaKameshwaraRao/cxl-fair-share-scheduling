import json, os
DATA = os.environ.get('DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'results', 'phase1'))
P = json.load(open(os.path.join(DATA, 'p1raw.json')))
S0 = {'tealeaf': 'v4tea', 'STREAM': 'stream24m', 'fotonik3d': 'v5foton', 'streamcluster': 'sc', 'roms': 'v5roms', 'LLM inference': 'llamar5', 'MERCI': 'merci4',
      'graph500': 'v5g500', 'hnswlib': 'v2hnsw', 'cactus': 'v5cactus', 'multichase': 'v6mchase', 'Marian': 'v5marian'}
SK = {'tealeaf': 'v4tea', 'STREAM': 'v2stream24m', 'fotonik3d': 'v5foton', 'streamcluster': 'v3sc', 'roms': 'v5roms', 'LLM inference': 'v2llamar5', 'MERCI': 'v2merci4',
      'graph500': 'v5g500', 'hnswlib': 'v2hnsw', 'cactus': 'v5cactus', 'multichase': 'v6mchase', 'Marian': 'v5marian'}
REQ = {'MERCI', 'multichase'}
def m(h):
    return dict(bw=h['reqs'] * 64 / h['secs'] / 1e9, lat=h['latsum'] / h['reqs'] / 1000 if h['reqs'] else 0, ips=h['insts'] / h['secs'] / 1e9, rps=h['reqs'] / h['secs'] / 1e6, h=h)
def alone(w, k):
    name = f'p1w_alone_{S0[w]}' if k == 0 else f'p1s_{SK[w]}_s{k}'
    if name == 'p1s_v3sc_s2': name = 'p1s_v3sc_s2_rerun'
    return m(P[name]['hosts'][0])
def pct(h, q):
    tot = sum(h['hist'].values()) + h['over']; acc = 0
    for b in sorted(h['hist'], key=int):
        acc += h['hist'][b]
        if acc >= q * tot: return int(b) * 5 + 2.5
    return float('inf')
