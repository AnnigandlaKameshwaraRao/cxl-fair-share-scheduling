"""Time-weighted pool bandwidth over a whole alone run: total pool packets x 64 B / total simulated time
(stats dumps are disjoint because every dump resets the counters). usage: tw_mean.py RUN_DIR..."""
import re, sys
p = 'board.remote_memory.outgoing_request_bridge.'
for run in sys.argv[1:]:
    s = open(f'{run}/btp_0/stats.txt').read().split('Begin Simulation Statistics')[1:]
    T = N = L = I = 0.0
    for b in s:
        g = lambda k: float(m.group(1)) if (m := re.search(r'^' + re.escape(k) + r'\s+(\S+)', b, re.M)) else 0.0
        t = g('simSeconds'); n = g(p + 'numReadOutgoingPackets') + g(p + 'numWriteOutgoingPackets')
        lat = g(p + 'packetLatency::mean'); fl = g(p + 'outstandingPackets::mean')
        T += t; N += n; L += lat * n; I += fl * t
    print(f'{run:32s} {T*1e3:6.1f} ms  {N*64/T/1e9:5.2f} GB/s  lat {L/N/1e3 if N else 0:4.0f} ns  inflight {I/T:4.1f}')
