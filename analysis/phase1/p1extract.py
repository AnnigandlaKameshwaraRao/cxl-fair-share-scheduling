import glob, json, os, re, sys
BR = 'board.remote_memory.outgoing_request_bridge.'
def host(path):
    o = dict(secs=0.0, reqs=0.0, rd=0.0, wr=0.0, insts=0.0, latsum=0.0, hist={}, over=0.0, dumps=0)
    for block in open(path, errors='ignore').read().split('---------- Begin Simulation Statistics ----------')[1:]:
        n = 0.0; lm = 0.0; o['dumps'] += 1
        for line in block.splitlines():
            p = line.split()
            if len(p) < 2: continue
            k = p[0]
            if k == 'simSeconds': o['secs'] += float(p[1])
            elif k == BR + 'numReadOutgoingPackets': n += float(p[1]); o['rd'] += float(p[1])
            elif k == BR + 'numWriteOutgoingPackets': n += float(p[1]); o['wr'] += float(p[1])
            elif k == BR + 'packetLatency::mean' and p[1] not in ('nan', 'inf'): lm = float(p[1])
            elif k.startswith(BR + 'packetLatency::') and re.fullmatch(r'[0-9.e+]+-[0-9.e+]+', k.split('::')[1]):
                lo = int(float(k.split('::')[1].split('-')[0]) / 5000); o['hist'][str(lo)] = o['hist'].get(str(lo), 0.0) + float(p[1])
            elif k == BR + 'packetLatency::overflows': o['over'] += float(p[1])
            elif re.fullmatch(r'board\.processor\.cores\d+\.core\.commitStats0\.numInsts', k): o['insts'] += float(p[1])
        o['reqs'] += n; o['latsum'] += lm * n
    return o
out = {}
D = os.path.expanduser('~/BTP/cxl-clustersim')
mixdir = {m: f'{D}/p1m_{m:02d}_desk' for m in range(1, 19)}
for m in (1, 4, 13): mixdir[m] = f'{D}/p1m_{m:02d}_clus'
for m, d in mixdir.items():
    cfg = json.load(open(f'{d}/job_config.json')) if os.path.exists(f'{d}/job_config.json') else {'0': {'metadata': {}}}
    out[f'mix{m}'] = dict(dir=d, comment=cfg['0']['metadata'].get('comment', ''), hosts=[host(f'{d}/btp_{h}/stats.txt') for h in range(4)])
for d in sorted(glob.glob(f'{D}/p1w_alone_*_a1') + glob.glob(f'{D}/p1s_*_a1')):
    out[os.path.basename(d)[:-3]] = dict(dir=d, hosts=[host(f'{d}/btp_0/stats.txt')])
d = os.path.expanduser('~/BTP/cxl-clustersim/p1s_v3sc_s2_a2'); out['p1s_v3sc_s2_rerun'] = dict(dir=d, hosts=[host(f'{d}/btp_0/stats.txt')])
json.dump(out, open('p1raw.json', 'w'))
print(len(out), 'runs')
