"""Independent recomputation from raw gem5 stats.txt files. Shares no code with the scripts that wrote the docs."""
import glob, os, re, json
HOME = os.path.expanduser('~')
# folders holding the raw run directories (<name>_a1/btp_<i>/stats.txt); set RUNS to override
ROOTS = os.environ.get('RUNS', f'{HOME}/BTP/cxl-clustersim').split(':')
BR = 'board.remote_memory.outgoing_request_bridge.'

def find(name):
    for r in ROOTS:
        c = [d for d in glob.glob(f'{r}/{name}') if os.path.isfile(f'{d}/btp_0/stats.txt')]
        if c: return sorted(c)[0]
    raise SystemExit(f'missing run {name}')

def host_stats(path):
    secs = reqs = insts = 0.0
    for block in open(path, errors='ignore').read().split('---------- Begin Simulation Statistics ----------')[1:]:
        for line in block.splitlines():
            p = line.split()
            if len(p) < 2: continue
            k = p[0]
            if k == 'simSeconds': secs += float(p[1])
            elif k in (BR + 'numReadOutgoingPackets', BR + 'numWriteOutgoingPackets'): reqs += float(p[1])
            elif re.fullmatch(r'board\.processor\.cores\d+\.core\.commitStats0\.numInsts', k): insts += float(p[1])
    return dict(secs=secs, ips=insts / secs, rps=reqs / secs, gbs=reqs * 64 / secs / 1e9)

def channels(d):
    f = f'{d}/job_config.json'
    if not os.path.exists(f): return None
    return json.load(open(f))['0']['metadata'].get('pool-channels')

def run(name, n):
    d = find(name)
    return d, [host_stats(f'{d}/btp_{h}/stats.txt') for h in range(n)]
