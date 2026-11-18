from campalone import *
ROLE = {w: ('aggressor' if w in ('tealeaf','STREAM','fotonik3d','streamcluster','roms','LLM inference') else 'victim') for w in TAG}
def f2(x): return f'{x:.2f}'
def bw(x): return f'{x:.3f}' if x < 0.1 else f'{x:.2f}'
def ip(x): return f'{x:.3f}' if x < 0.1 else f'{x:.2f}'
def pc(x, d=1):
    s = f'{x:+.{d}f}%'
    if float(s[:-1]) == 0: return f'{0:.{d}f}%'
    return s.replace('-', '−')
def ns(x): return f'{x:.0f}'
out = {}
# 1 channel
L = ['| Workload | Role | Bandwidth FR-FCFS (GB/s) | Bandwidth PAR-BS (GB/s) | Latency FR-FCFS (ns) | Latency PAR-BS (ns) | Instr. rate FR-FCFS (G/s) | Instr. rate PAR-BS (G/s) | Row-hit rate FR-FCFS | Row-hit rate PAR-BS |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for w in TAG:
    L.append(f"| {w} | {ROLE[w]} | {bw(mean('o1fr',w,'bw'))} | {bw(mean('p1',w,'bw'))} | {ns(mean('o1fr',w,'lat'))} | {ns(mean('p1',w,'lat'))} | {ip(mean('o1fr',w,'ips'))} | {ip(mean('p1',w,'ips'))} | {f2(mean('o1fr',w,'rh'))} | {f2(mean('p1',w,'rh'))} |")
out['t1'] = '\n'.join(L)
L = ['| Workload | Bandwidth FCFS (GB/s) | Bandwidth FR-FCFS (GB/s) | Bandwidth PAR-BS (GB/s) | Latency FCFS (ns) | Latency FR-FCFS (ns) | Latency PAR-BS (ns) | Instr. rate FCFS (G/s) | Instr. rate FR-FCFS (G/s) | Instr. rate PAR-BS (G/s) | Row-hit rate FR-FCFS | Row-hit rate PAR-BS |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for w in TAG:
    L.append(f"| {w} | {bw(mean('n2fc',w,'bw'))} | {bw(mean('n2fr',w,'bw'))} | {bw(mean('p2',w,'bw'))} | {ns(mean('n2fc',w,'lat'))} | {ns(mean('n2fr',w,'lat'))} | {ns(mean('p2',w,'lat'))} | {ip(mean('n2fc',w,'ips'))} | {ip(mean('n2fr',w,'ips'))} | {ip(mean('p2',w,'ips'))} | {f2(mean('n2fr',w,'rh'))} | {f2(mean('p2',w,'rh'))} |")
out['t2'] = '\n'.join(L)
def same(a,b,w,k):
    x=R[f"{SETS[a][0]}_{TAG[w]}_s{k}"]['hosts'][0]; y=R[f"{SETS[b][0]}_{TAG[w]}_s{k}"]['hosts'][0]
    return x['insts']==y['insts'] and x['reqs']==y['reqs'] and x['latsum']==y['latsum']
def slots(a,b,w,key='ips'):
    return ' / '.join(('0.00%' if A[(a,w,k)][key]==A[(b,w,k)][key] else pc(100*(A[(a,w,k)][key]/A[(b,w,k)][key]-1),2)) for k in range(4))
L = ['| Workload | FCFS: runs identical to O3 (of 4) | FCFS: instr. rate change, slots 0 / 1 / 2 / 3 | FR-FCFS: runs identical to O3 (of 4) | FR-FCFS: instr. rate change, slots 0 / 1 / 2 / 3 |', '| --- | --- | --- | --- | --- |']
for w in TAG:
    L.append(f"| {w} | {sum(same('n2fc','o2fc',w,k) for k in range(4))} | {slots('n2fc','o2fc',w)} | {sum(same('n2fr','o2fr',w,k) for k in range(4))} | {slots('n2fr','o2fr',w)} |")
out['t5'] = '\n'.join(L)
out['ident'] = (sum(same('n2fc','o2fc',w,k) for w in TAG for k in range(4)), sum(same('n2fr','o2fr',w,k) for w in TAG for k in range(4)))
L = ['| Workload | 1 ch: instr. rate | 1 ch: pool bandwidth | 1 ch: latency (ns) | 1 ch: row-hit rate, FR-FCFS → PAR-BS | 2 ch: instr. rate | 2 ch: pool bandwidth | 2 ch: latency (ns) | 2 ch: row-hit rate, FR-FCFS → PAR-BS |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
def dl(a,b,w): v = st.mean(A[(a,w,k)]['lat']-A[(b,w,k)]['lat'] for k in range(4)); s=f'{v:+.0f}'.replace('-','−'); return '0' if s in ('+0','−0') else s
for w in TAG:
    L.append(f"| {w} | {pc(100*chg('p1','o1fr',w))} | {pc(100*chg('p1','o1fr',w,'bw'))} | {dl('p1','o1fr',w)} | {f2(mean('o1fr',w,'rh'))} → {f2(mean('p1',w,'rh'))} | {pc(100*chg('p2','n2fr',w))} | {pc(100*chg('p2','n2fr',w,'bw'))} | {dl('p2','n2fr',w)} | {f2(mean('n2fr',w,'rh'))} → {f2(mean('p2',w,'rh'))} |")
out['t6'] = '\n'.join(L)
L = ['| Workload | L3 prefetches, 1 ch FR-FCFS | L3 prefetches, 1 ch PAR-BS | L3 demand misses, 1 ch FR-FCFS | L3 demand misses, 1 ch PAR-BS |', '| --- | --- | --- | --- | --- |']
for w in ('tealeaf','STREAM','fotonik3d','roms','MERCI'):
    L.append(f"| {w} | {mean('o1fr',w,'pf'):.1f} | {mean('p1',w,'pf'):.1f} | {mean('o1fr',w,'mm'):.1f} | {mean('p1',w,'mm'):.1f} |")
out['t6b'] = '\n'.join(L)
L = ['| Workload | 1 ch: instr. rate change, slots 0 / 1 / 2 / 3 | 1 ch: row-hit rate PAR-BS, slots 0–3 | 2 ch: instr. rate change, slots 0 / 1 / 2 / 3 | 2 ch: row-hit rate PAR-BS, slots 0–3 |', '| --- | --- | --- | --- | --- |']
for w in TAG:
    L.append(f"| {w} | {slots('p1','o1fr',w)} | {' / '.join(f2(A[('p1',w,k)]['rh']) for k in range(4))} | {slots('p2','n2fr',w)} | {' / '.join(f2(A[('p2',w,k)]['rh']) for k in range(4))} |")
out['t7'] = '\n'.join(L)
L = ['| Workload | Row-hit rate, 2 ch FCFS (mean) | Slots 0 / 1 / 2 / 3 | Row-hit rate, 2 ch FR-FCFS (mean) |', '| --- | --- | --- | --- |']
for w in sorted(TAG, key=lambda w: -mean('n2fc',w,'rh')):
    L.append(f"| {w} | {f2(mean('n2fc',w,'rh'))} | {' / '.join(f2(A[('n2fc',w,k)]['rh']) for k in range(4))} | {f2(mean('n2fr',w,'rh'))} |")
out['t8'] = '\n'.join(L)
out['merci'] = {s: [round(A[(s,'MERCI',k)]['bw'],3) for k in range(4)] for s in ('o1fr','p1','n2fr','p2')}
out['mercichg'] = {'1bw': slots('p1','o1fr','MERCI','bw'), '2bw': slots('p2','n2fr','MERCI','bw'), 'mc1bw': slots('p1','o1fr','multichase','bw')}
json.dump(out, open('camp_tables.json','w'), indent=1)
for k,v in out.items(): print('=====',k); print(v)
