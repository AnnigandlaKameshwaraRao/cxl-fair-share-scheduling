"""Phase 1 - Mixed, final: every mix host vs the same workload alone from the SAME checkpoint slot.
All rates are per simulated second, so small differences in window length (390-443 ms) cancel.
Progress per host: instructions/s, except merci and multichase where pool requests/s is used
(their instruction counts include spin/idle loops that grow when they stall).
Slowdown = alone progress rate / mix progress rate."""
import re, os, json, statistics as st
R = os.path.expanduser('~/cxl-clustersim'); D = os.path.dirname(os.path.abspath(__file__))
SLOT0 = {'v4tea': 'p1w_alone_v4tea_a1', 'v2stream24m': 'p1w_alone_stream24m_a1', 'v5foton': 'p1w_alone_v5foton_a1',
         'v3sc': 'p1w_alone_sc_a1', 'v5roms': 'p1w_alone_v5roms_a1', 'v2llamar5': 'p1w_alone_llamar5_a1',
         'v2merci4': 'p1w_alone_merci4_a1', 'v5g500': 'p1w_alone_v5g500_a1', 'v2hnsw': 'p1w_alone_v2hnsw_a1',
         'v5cactus': 'p1w_alone_v5cactus_a1', 'v6mchase': 'p1w_alone_v6mchase_a1', 'v5marian': 'p1w_alone_v5marian_a1'}
NAME = {'v4tea': 'tealeaf', 'v2stream24m': 'STREAM', 'v5foton': 'fotonik3d', 'v3sc': 'streamcluster', 'v5roms': 'roms',
        'v2llamar5': 'llama', 'v2merci4': 'merci', 'v5g500': 'graph500', 'v2hnsw': 'hnswlib', 'v5cactus': 'cactus',
        'v6mchase': 'multichase', 'v5marian': 'marian'}
REQ = {'v2merci4', 'v6mchase'}   # progress = pool requests
FIXED = {('v3sc', 2): 'p1s_v3sc_s2_a2'}   # slot-2 streamcluster rerun with the remade checkpoint
p = 'board.remote_memory.outgoing_request_bridge.'
CACHE = f'{D}/analyse2_cache.json'
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def host(f):
    key = f'{f}:{os.path.getmtime(f)}'
    if key in cache: return cache[key]
    T = N = L = I = 0.0
    for b in open(f).read().split('Begin Simulation Statistics')[1:]:
        g = lambda k: float(m.group(1)) if (m := re.search(r'^' + re.escape(k) + r'\s+(\S+)', b, re.M)) else 0.0
        n = g(p + 'numReadOutgoingPackets') + g(p + 'numWriteOutgoingPackets')
        T += g('simSeconds'); N += n; L += g(p + 'packetLatency::mean') * n
        I += sum(float(x) for x in re.findall(r'^board\.processor\.cores\d+\.core\.commitStats0\.numInsts\s+(\S+)', b, re.M))
    r = dict(ms=T * 1e3, bw=N * 64 / T / 1e9, lat=L / N / 1e3 if N else 0, ips=I / T, rps=N / T)
    cache[key] = r; return r

def alone_dir(w, k):
    return FIXED.get((w, k)) or (SLOT0[w] if k == 0 else f'p1s_{w}_s{k}_a1')

def mix_dir(n):
    d = f'{R}/p1m_{n:02d}_desk'
    return d if os.path.isdir(d) else f'{R}/p1m_{n:02d}_clus'

mixmap = {}
for l in open(f'{D}/ckpt_map.txt'):
    m, i, w = l.split(); mixmap.setdefault(int(m[4:]), {})[int(i)] = w[3:]

out = {'mixes': {}, 'slots': {}}
for w in SLOT0:   # slot-to-slot spread of the alone runs
    rows = [host(f'{R}/{alone_dir(w, k)}/btp_0/stats.txt') for k in range(4)]
    out['slots'][w] = rows
for n in sorted(mixmap):
    rows = []
    for i in range(4):
        w = mixmap[n][i]
        a = host(f'{R}/{alone_dir(w, i)}/btp_0/stats.txt'); m = host(f'{mix_dir(n)}/btp_{i}/stats.txt')
        a0 = host(f'{R}/{SLOT0[w]}/btp_0/stats.txt')
        k = 'rps' if w in REQ else 'ips'
        rows.append(dict(w=w, slot=i, alone=a, mix=m, sd=a[k] / m[k], sd_slot0=a0[k] / m[k]))
    sp = [1 / r['sd'] for r in rows]
    out['mixes'][n] = dict(rows=rows, pool=sum(r['mix']['bw'] for r in rows), demand=sum(r['alone']['bw'] for r in rows),
                           ws=sum(sp), maxsd=max(r['sd'] for r in rows), minsd=min(r['sd'] for r in rows),
                           jain=sum(sp) ** 2 / (4 * sum(x * x for x in sp)))
json.dump(cache, open(CACHE, 'w'))
json.dump(out, open(f'{D}/analyse2_out.json', 'w'), indent=1)

print('ALONE RUNS: slot-to-slot spread (pool GB/s and progress rate, slots 0-3)')
for w, rows in out['slots'].items():
    k = 'rps' if w in REQ else 'ips'; v = [r[k] for r in rows]
    print(f'  {NAME[w]:13s} bw ' + ' '.join(f'{r["bw"]:5.2f}' for r in rows) +
          f'   rate spread {max(v) / min(v):.2f}x  ' + ('(requests/s)' if w in REQ else '(insts/s)'))
print('\nMIXES (sorted by alone demand): pool GB/s used of demanded, weighted speedup, worst and best slowdown, Jain')
for n, x in sorted(out['mixes'].items(), key=lambda t: t[1]['demand']):
    print(f'mix {n:2d}: demand {x["demand"]:5.2f} -> got {x["pool"]:5.2f} GB/s  WS {x["ws"]:.2f}/4  '
          f'max {x["maxsd"]:.2f}x  min {x["minsd"]:.2f}x  Jain {x["jain"]:.3f}')
    for r in x['rows']:
        a, m = r['alone'], r['mix']
        print(f'    s{r["slot"]} {NAME[r["w"]]:13s} bw {a["bw"]:5.2f} -> {m["bw"]:5.2f}  lat {a["lat"]:4.0f} -> {m["lat"]:4.0f} ns'
              f'  slowdown {r["sd"]:.2f}x' + (f'  (vs slot-0 baseline {r["sd_slot0"]:.2f}x)' if r['slot'] else ''))
