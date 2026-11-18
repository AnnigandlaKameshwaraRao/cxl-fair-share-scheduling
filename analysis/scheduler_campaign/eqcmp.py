#!/usr/bin/env python3
"""Equivalence check: compare alone runs dump by dump (gem5 stats.txt, host-timing stats excluded)
and the SST pool statistics (sst-output_0.txt, common statistics only)."""
import re, sys, os

HOSTSTAT = re.compile(r'^(host|sim_seconds_per)')


def dumps(run):
    t = open(f'{run}/btp_0/stats.txt').read().split('---------- Begin Simulation Statistics ----------')[1:]
    out = []
    for s in t:
        d = {}
        for l in s.splitlines():
            p = l.split()
            if len(p) < 2 or p[0].startswith('-'):
                continue
            if HOSTSTAT.match(p[0].split('.')[-1]):
                continue
            d[p[0]] = p[1:]
        out.append(d)
    return out


def sst(run):
    d = {}
    for l in open(f'{run}/sst-output_0.txt'):
        m = re.match(r'^(\S+) : Accumulator : SimTime = (\d+); Rank = \d+; (.*)$', l.strip())
        if m:
            d[m.group(1)] = (m.group(2), m.group(3))
    return d


def val(d, k):
    v = d.get(k)
    return float(v[0]) if v and re.match(r'^-?[\d.e+]+$', v[0]) else None


def summary(ds):
    """instructions committed (sum over cores) and remote (pool) reads per dump"""
    rows = []
    for d in ds:
        ins = sum(float(v[0]) for k, v in d.items() if re.match(r'board\.processor\.cores\d\.core\.commitStats0\.numInsts$', k))
        rows.append(ins)
    return rows


def compare(ref, run):
    a, b = dumps(ref), dumps(run)
    n = min(len(a), len(b))
    diff = []
    for i in range(n):
        ka, kb = set(a[i]), set(b[i])
        dk = [k for k in ka & kb if a[i][k] != b[i][k]]
        only = (ka ^ kb)
        if dk or only:
            diff.append((i, len(dk), len(only), sorted(dk)[:5]))
    sa, sb = sst(ref), sst(run)
    common = set(sa) & set(sb)
    sdiff = sorted(k for k in common if sa[k] != sb[k])
    return len(a), len(b), diff, len(common), sdiff, sorted(set(sb) - set(sa)), sorted(set(sa) - set(sb)), sa, sb


if __name__ == '__main__':
    pairs = [l.split() for l in sys.stdin if l.strip()]
    for ref, run in pairs:
        na, nb, diff, nc, sdiff, onlyb, onlya, sa, sb = compare(ref, run)
        print(f'== {os.path.basename(run)}  vs  {os.path.basename(ref)}')
        print(f'   dumps {nb} vs {na}; gem5 dumps differing: {[d[0] + 1 for d in diff]}')
        for i, ndk, nonly, ex in diff[:3]:
            print(f'     dump {i + 1}: {ndk} stats differ, {nonly} only in one; e.g. {ex}')
        print(f'   SST pool stats: {nc} in common, {len(sdiff)} differ; only in run: {onlyb}; only in ref: {onlya}')
        for k in sdiff[:8]:
            print(f'     {k}: ref {sa[k][1][:70]} | run {sb[k][1][:70]}')
