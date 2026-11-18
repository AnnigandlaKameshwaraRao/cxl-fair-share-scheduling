"""Pool traffic per stats dump, on the time axis since restore.
usage: python3 win_series.py RUN_DIR CKPT_DIR   (prints one row per dump, per host)"""
import sys, re, os
run, ck = sys.argv[1], sys.argv[2]
P = 'board.remote_memory.outgoing_request_bridge.'
for h in sorted(d for d in os.listdir(run) if d.startswith('btp_')):
    t0 = int(re.search(r'^curTick=(\d+)', open(f'{ck}/{h}/checkpoint/m5.cpt').read(), re.M).group(1))
    print(f'== {h}   start-end(ms)  insts(M)  poolBW(GB/s)  lat(ns)  inflight')
    for b in open(f'{run}/{h}/stats.txt').read().split('Begin Simulation Statistics')[1:]:
        def g(k):
            m = re.search(r'^' + re.escape(k) + r'\s+(\S+)', b, re.M)
            return float(m.group(1)) if m else float('nan')
        t = g('simSeconds'); end = (g('finalTick') - t0) / 1e9
        if t < 1e-4: continue
        n = g(P + 'numReadOutgoingPackets') + g(P + 'numWriteOutgoingPackets')
        print(f'   {end - t*1e3:6.1f}-{end:6.1f}  {g("simInsts")/1e6:8.1f}  {n*64/t/1e9:8.2f}  '
              f'{g(P+"packetLatency::mean")/1e3:7.0f}  {g(P+"outstandingPackets::mean"):6.1f}')
