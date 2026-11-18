import re, sys
sys.argv = ['x']; exec(open('check.py').read().replace("print('problems:'", "_=('problems:'").replace("print('mix workloads:'", "_=('mix workloads:'"))
MIXES = ('m04', 'm13', 'm01')
def norm(label):
    l = label.replace('*', '').strip()
    l = {'SAA, smoothing 0.75': 'SAA, smoothing', '10M': 'ATLAS 10M', '10M + rule': 'ATLAS 10M + rule', '1M': 'ATLAS 1M', '1M + rule': 'ATLAS 1M + rule'}.get(l, l)
    return l
COL = {'largest slowdown': 'max', 'unfairness': 'unf', 'weighted speedup': 'ws', 'slowdown': 'mean', 'spread (cv)': 'cv', 'jain, progress': 'jp',
       'jain, bandwidth share': 'jbs', 'bandwidth-share unfairness': 'bsu', 'jain, raw bandwidth': 'jbw', 'harmonic speedup': 'hs', 'delivered (gb/s)': 'gbs', 'largest': 'max'}
def value(doc, sch, col, mix):
    base = 'fcfs' if (doc == 'fcfs' or sch == 'FCFS') else 'frfcfs'
    c = col.lower()
    mm = re.match(r'largest (m\d\d)$', c)
    if mm: return metrics(sch, mm.group(1), base)['max']
    if c == 'mean slowdown' and mix: return metrics(sch, mix, base)['mean']
    if c.startswith('mean '):
        k = COL[c[5:]]; return sum(metrics(sch, m, base)[k] for m in MIXES) / 3
    if c in COL and mix: return metrics(sch, mix, base)[COL[c]]
    if mix and c in [w.lower() for w in WL[mix]]: return metrics(sch, mix, base)['sd'][[w.lower() for w in WL[mix]].index(c)]
    return None
def check(doc, path):
    lines = open(path).read().splitlines(); mix = None; n = bad = 0; skipped = set()
    i = 0
    while i < len(lines):
        l = lines[i]
        h = re.match(r'#+ (m\d\d)', l)
        if h: mix = h.group(1)
        elif l.startswith('#'): mix = None
        if l.startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
            hdr = [c.strip() for c in l.strip('|').split('|')]; i += 2
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip('|').split('|')]; row = norm(cells[0])
                for col, cell in zip(hdr[1:], cells[1:]):
                    txt = cell.replace('*', '')
                    if not re.fullmatch(r'-?\d+\.\d+', txt): skipped.add(f'{hdr[0]}/{col}'); continue
                    sch, cmix, ccol = row, mix, col
                    mm = re.match(r'(m\d\d) \(', row)
                    if mm:  # SAA table: rows are mixes, cols name scheduler
                        cmix = mm.group(1); metric, who = col.split(': '); sch = 'SAA' if who == 'SAA' else 'SAA, smoothing'
                        ccol = {'Largest': 'largest slowdown', 'Unfairness': 'unfairness', 'Weighted speedup': 'weighted speedup'}.get(metric)
                        if metric == 'Host 3':
                            v = metrics(sch, cmix, 'frfcfs' if doc == 'frfcfs' else 'fcfs')['sd'][3]
                        else: v = value(doc, sch, ccol, cmix)
                    elif sch in SCHED: v = value(doc, sch, ccol, cmix)
                    else: v = None
                    if v is None: skipped.add(f'{hdr[0]}/{col} row {row}'); continue
                    dec = len(txt.split('.')[1]); got = float(txt); exp = round(v, dec); n += 1
                    if abs(got - exp) > 10 ** -dec * 1.01:
                        bad += 1; print(f'  MISMATCH {doc} [{mix or "-"}] {row} / {col}: doc {txt}, computed {v:.4f}')
                    elif got != exp: print(f'  rounding {doc} [{mix or "-"}] {row} / {col}: doc {txt}, computed {v:.4f}')
                i += 1
            continue
        i += 1
    print(f'{doc}: {n} cells checked, {bad} mismatches; not checked here: {sorted(skipped)}')
check('frfcfs', '../ana/doc_frfcfs.md'); check('fcfs', '../ana/doc_fcfs.md')

# extra tables: rule firing counts (from logs) and alone ratios / row-hit rates (from raw files)
import glob
print('rule counts:')
for name in ('s1m_atlasr_m04', 's1m_atlas1mr_m04', 's1m_atlasr_m13', 's1m_atlas1mr_m13', 's1m_atlasr_m01', 's1m_atlas1mr_m01'):
    logs = [f for r in ROOTS for f in glob.glob(f'{r}/{name}_a1_full_log.txt')]
    for f in logs[:1]:
        m = re.findall(r'BTP_ATLAS_END over_threshold_admits=(\S+)', open(f, errors='ignore').read())
        print(' ', name, m[-1] if m else 'none')
print('alone ratio FR-FCFS/FCFS and FR-FCFS alone row-hit:')
for (w, slot) in [('tealeaf', 0), ('STREAM', 1), ('fotonik3d', 1), ('fotonik3d', 2), ('roms', 2), ('MERCI', 3), ('streamcluster', 3), ('multichase', 3)]:
    a, b = alone[('frfcfs', w, slot)], alone[('fcfs', w, slot)]
    rh = None
    for wave in ('o3a', 'o3e'):
        for r in ROOTS:
            for f in glob.glob(f'{r}/{wave}_frfcfs_{TAG[w]}_s{slot}_a1_full_log.txt'):
                m = re.findall(r'BTP_ROWSTATS.*rowhit=(\S+)', open(f, errors='ignore').read()); rh = rh or (m[-1] if m else None)
    print(f'  {w} s{slot}: {prog(a, w) / prog(b, w):.3f}  rowhit {rh}')
