"""Every mix run folder (o3b_, s1m_, s2m_) under the given roots: raw gem5 stats per host (as extract2.host), dump counts,
max_ticks lines, pool row stats, config. One JSON line per folder (all copies, so duplicates can be compared)."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extract2.py')).read().split('for root in sys.argv')[0]
exec(src)   # defines host()
def one(d):
    if True:
        name = os.path.basename(d)[:-3]
        if not os.path.exists(f'{d}/job_config.json'): return None
        cfg = json.load(open(f'{d}/job_config.json')); md = cfg['0']['metadata']
        hosts = sorted(int(x.split('_')[-1]) for x in glob.glob(f'{d}/btp_[0-9]'))
        dumps = [open(f'{d}/btp_{h}/stats.txt', errors='ignore').read().count('Begin Simulation Statistics') if os.path.exists(f'{d}/btp_{h}/stats.txt') else 0 for h in hosts]
        log = d + '_full_log.txt'; rs = None; mt = None
        if os.path.exists(log):
            t = open(log, errors='ignore').read()
            m = re.findall(r'BTP_ROWSTATS PRE=(\d+) ACT=(\d+) COL=(\d+) rowhit=(\S+)', t)
            rs = [list(map(float, x)) for x in m]; mt = t.count('max_ticks reached')
        out = dict(name=name, dir=os.path.abspath(d), channels=md.get('pool-channels'), sched=md.get('pool-sched'), arb=md.get('pool-arb'),
                   params=md.get('pool-arb-params'), comment=md.get('comment'), maxticks=md.get('max-ticks'),
                   cmds=[json.dumps(cfg[str(h)]) for h in hosts], dumps=dumps, maxticks_lines=mt, rowstats=rs,
                   hosts=[host(f'{d}/btp_{h}/stats.txt') if os.path.exists(f'{d}/btp_{h}/stats.txt') else None for h in hosts])
        return json.dumps(out)

if __name__ == '__main__':
    from multiprocessing import Pool
    ds = sorted(d for root in sys.argv[1:] for p in ('o3b', 's1m', 's2m') for d in glob.glob(f'{root}/{p}_*_a1'))
    with Pool(12) as P:
        for o in P.imap(one, ds):
            if o: print(o, flush=True)
