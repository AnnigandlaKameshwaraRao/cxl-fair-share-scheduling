"""Walk run folders, read raw gem5 stats + job config + pool row-hit line; print one JSON line per run."""
import glob, json, os, re, sys
BR = 'board.remote_memory.outgoing_request_bridge.'
def host(path):
    secs = reqs = insts = lat = pf = mm = pfid = 0.0
    for block in open(path, errors='ignore').read().split('---------- Begin Simulation Statistics ----------')[1:]:
        n = 0.0; lm = 0.0
        for line in block.splitlines():
            p = line.split()
            if len(p) < 2: continue
            k = p[0]
            if k == 'simSeconds': secs += float(p[1])
            elif k in (BR + 'numReadOutgoingPackets', BR + 'numWriteOutgoingPackets'): n += float(p[1])
            elif k == BR + 'packetLatency::mean' and p[1] not in ('nan', 'inf'): lm = float(p[1])
            elif re.fullmatch(r'board\.processor\.cores\d+\.core\.commitStats0\.numInsts', k): insts += float(p[1])
            elif k == 'board.cache_hierarchy.l3cache.prefetcher.pfIssued': pf += float(p[1])
            elif k == 'board.cache_hierarchy.l3cache.prefetcher.pfIdentified': pfid += float(p[1])
            elif k == 'board.cache_hierarchy.l3cache.demandMshrMisses::total': mm += float(p[1])
        reqs += n; lat += lm * n
    return dict(secs=secs, reqs=reqs, insts=insts, latsum=lat, pf=pf, pfid=pfid, mshrmiss=mm)
for root in sys.argv[1:]:
    for d in sorted(d for d in glob.glob(f'{root}/o3*_a1') if not re.match(r'o3[bd]_', os.path.basename(d))):
        name = os.path.basename(d)[:-3]
        if not os.path.exists(f'{d}/btp_0/stats.txt') or not os.path.exists(f'{d}/job_config.json'): continue
        cfg = json.load(open(f'{d}/job_config.json'))
        hosts = sorted(int(x.split('_')[-1]) for x in glob.glob(f'{d}/btp_[0-9]'))
        log = d + '_full_log.txt'; rh = None
        if os.path.exists(log):
            m = re.findall(r'BTP_ROWSTATS.*?rowhit=(\S+)', open(log, errors='ignore').read()); rh = m[-1] if m else None
        out = dict(name=name, dir=d, channels=cfg['0']['metadata'].get('pool-channels'), sched=cfg['0']['metadata'].get('pool-sched'),
                   cmds=[json.dumps(cfg[str(h)]) for h in hosts], hosts=[host(f'{d}/btp_{h}/stats.txt') for h in hosts], rowhit=rh)
        print(json.dumps(out), flush=True)
