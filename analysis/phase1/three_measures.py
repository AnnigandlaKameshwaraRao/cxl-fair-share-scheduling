import json
o=json.load(open('analyse2_out.json'))
N={'v4tea':'tealeaf','v2stream24m':'STREAM','v5foton':'fotonik3d','v3sc':'streamcluster','v5roms':'roms','v2llamar5':'LLM inference','v2merci4':'MERCI','v5g500':'graph500','v2hnsw':'hnswlib','v5cactus':'cactus','v6mchase':'multichase','v5marian':'Marian'}
SPIN={'v2merci4','v6mchase'}
UNL=245.0
pct=lambda a,b:(b/a-1)*100
f=lambda v:f"{v:+.0f}%".replace('+-','-').replace('-0%','0%') if abs(v)>=0.5 else '0%'
# ALONE per-slot table
L=['| Workload | Slot | Pool GB/s | Pool latency (ns) | Latency above unloaded 245 ns | Instructions (billion per simulated s) | Instruction rate vs slot 0 | Pool requests (million per simulated s) |','| --- | --- | --- | --- | --- | --- | --- | --- |']
for w,rows in o['slots'].items():
  for k,r in enumerate(rows):
    L.append(f"| {N[w] if k==0 else ''} | {k} | {r['bw']:.2f} | {r['lat']:.0f} | {f(pct(UNL,r['lat']))} | {r['ips']/1e9:.3f} | {'—' if k==0 else f(pct(rows[0]['ips'],r['ips']))} | {r['rps']/1e6:.2f} |")
open('alone_table.md','w').write('\n'.join(L))
# MIX per-host + summary
H=['| Mix | Slot | Workload | Pool latency alone → mix (ns) | Latency increase | Instructions alone → mix (billion/s) | Instruction rate change | Pool requests alone → mix (million/s) | Request rate change |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
S=['| Mix | Workloads (slots 0–3) | Demand alone (GB/s) | Pool delivered (GB/s) | Latency increase, lowest–highest host | Instruction rate change, worst host | Instruction rate change, best host | Weighted speedup by instructions (of 4) | Jain by instructions |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
pts=[]; summ={}
for n,x in sorted(o['mixes'].items(),key=lambda t:t[1]['demand'],reverse=True):
  rs=x['rows']; lat=[pct(r['alone']['lat'],r['mix']['lat']) for r in rs]; ins=[pct(r['alone']['ips'],r['mix']['ips']) for r in rs]
  ratio=[r['mix']['ips']/r['alone']['ips'] for r in rs]; ws=sum(ratio); jain=ws**2/(4*sum(q*q for q in ratio))
  iw=min(range(4),key=lambda i:ins[i]); ib=max(range(4),key=lambda i:ins[i])
  S.append(f"| {n} | {', '.join(N[r['w']] for r in rs)} | {x['demand']:.1f} | {x['pool']:.1f} | {f(min(lat))} to {f(max(lat))} | {N[rs[iw]['w']]} {f(ins[iw])} | {N[rs[ib]['w']]} {f(ins[ib])} | {ws:.2f} | {jain:.2f} |")
  summ[n]=dict(ws=ws,jain=jain)
  for i,r in enumerate(rs):
    a,m=r['alone'],r['mix']; star='*' if r['w'] in SPIN else ''
    H.append(f"| {n} | {i} | {N[r['w']]}{star} | {a['lat']:.0f} → {m['lat']:.0f} | {f(lat[i])} | {a['ips']/1e9:.3f} → {m['ips']/1e9:.3f} | {f(ins[i])} | {a['rps']/1e6:.2f} → {m['rps']/1e6:.2f} | {f(pct(a['rps'],m['rps']))} |")
    pts.append(dict(id=f"m{int(n):02d}h{i}",mix=int(n),wl=N[r['w']],own=round(a['bw'],2),cls='light' if a['bw']<1.5 else 'heavy',spin=r['w'] in SPIN,demand=round(x['demand'],2),lat=round(lat[i]),ins=round(ins[i]),req=round(pct(a['rps'],m['rps']))))
open('mix_hosts.md','w').write('\n'.join(H)); open('mix_summary.md','w').write('\n'.join(S)); json.dump(pts,open('pts.json','w')); json.dump(summ,open('summ.json','w'))
print('\n'.join(S))
