import json, os, re, statistics as st, sys
from raw import *
KW = [('streamcluster', 'streamcluster'), ('stream.hw', 'STREAM'), ('tealeaf', 'tealeaf'), ('fotonik3d', 'fotonik3d'),
      ('roms', 'roms'), ('merci', 'MERCI'), ('multichase', 'multichase')]
REQ = {'MERCI', 'multichase'}
TAG = {'tealeaf': 'v4tea', 'fotonik3d': 'v5foton', 'roms': 'v5roms', 'MERCI': 'v2merci4', 'STREAM': 'v2stream24m',
       'streamcluster': 'v3sc', 'multichase': 'v6mchase'}
def wl_of(cfg_host):
    s = json.dumps(cfg_host)
    for k, n in KW:
        if k in s: return n
def cfg_of(name, d):
    f = f'{d}/job_config.json'
    if os.path.exists(f): return json.load(open(f))
    return json.load(open(f'{HOME}/cxl-clustersim/disaggregated_memory/exp_{name[:-3]}.json'))
SCHED = {'FCFS': 'o3b_fcfs', 'FR-FCFS': 'o3b_frfcfs', 'ATLAS 10M': 's1m_atlas', 'ATLAS 10M + rule': 's1m_atlasr', 'ATLAS 1M': 's1m_atlas1m',
         'ATLAS 1M + rule': 's1m_atlas1mr', 'TCM': 's1m_tcm', 'BLISS': 's1m_bliss', 'PAR-BS': 's1m_parbs', 'SAA': 's1m_saa', 'SAA, smoothing': 's1m_saasm'}
problems = []
mixes, alone = {}, {}
for sch, pre in SCHED.items():
    for m in ('m04', 'm13', 'm01'):
        name = f'{pre}_{m}_a1'; d, hs = run(name, 4); cfg = cfg_of(name, d)
        ch = cfg['0']['metadata'].get('pool-channels')
        if str(ch) != '1': problems.append(f'{name}: channels {ch}')
        if any(abs(h['secs'] - 0.1) > 0.0011 for h in hs): problems.append(f'{name}: covered seconds {[round(h["secs"],4) for h in hs]}')
        mixes[(sch, m)] = [(wl_of(cfg[str(i)]), hs[i]) for i in range(4)]
WL = {m: [w for w, _ in mixes[('FR-FCFS', m)]] for m in ('m04', 'm13', 'm01')}
for (sch, m), v in mixes.items():
    if [w for w, _ in v] != WL[m]: problems.append(f'{sch} {m}: workloads {[w for w,_ in v]} != {WL[m]}')
for base in ('fcfs', 'frfcfs'):
    for m, ws in WL.items():
        for slot, w in enumerate(ws):
            if (base, w, slot) in alone: continue
            name = None
            for wave in ('o3a', 'o3e'):
                try: d, hs = run(f'{wave}_{base}_{TAG[w]}_s{slot}_a1', 1); name = f'{wave}_{base}_{TAG[w]}_s{slot}'; break
                except SystemExit: pass
            if not name: problems.append(f'no alone {base} {w} s{slot}'); continue
            cfg = cfg_of(name + '_a1', d)
            if str(cfg['0']['metadata'].get('pool-channels')) != '1': problems.append(f'{name}: not 1 channel')
            if cfg['0']['metadata'].get('pool-sched') != base: problems.append(f'{name}: sched {cfg["0"]["metadata"].get("pool-sched")}')
            if wl_of(cfg['0']) != w: problems.append(f'{name}: workload {wl_of(cfg["0"])}')
            alone[(base, w, slot)] = hs[0]
def prog(h, w): return h['rps'] if w in REQ else h['ips']
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
def metrics(sch, m, base):
    v = mixes[(sch, m)]
    sd = [prog(alone[(base, w, i)], w) / prog(h, w) for i, (w, h) in enumerate(v)]
    bws = [h['gbs'] / alone[(base, w, i)]['gbs'] for i, (w, h) in enumerate(v)]
    bw = [h['gbs'] for _, h in v]
    return dict(sd=sd, max=max(sd), unf=max(sd) / min(sd), ws=sum(1 / x for x in sd), mean=st.mean(sd), cv=st.pstdev(sd) / st.mean(sd),
                jp=jain([1 / x for x in sd]), jbs=jain(bws), bsu=max(bws) / min(bws), jbw=jain(bw), hs=4 / sum(sd), gbs=sum(bw))
json.dump(dict(problems=problems), open('problems.json', 'w'))
print('problems:', problems or 'none')
print('mix workloads:', WL)
