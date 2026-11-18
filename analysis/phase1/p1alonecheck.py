from p1common import *
import re
res = {'ok': 0, 'round': [], 'bad': []}
def cmp(where, txt, val):
    t = txt.strip().replace('−', '-').replace('+', '').rstrip('%').replace(',', '')
    if not re.fullmatch(r'-?\d+(\.\d+)?', t): return
    dec = len(t.split('.')[1]) if '.' in t else 0; got, exp = float(t), round(val, dec)
    if got == exp: res['ok'] += 1
    elif abs(got - exp) <= 10 ** -dec * 1.01: res['round'].append(f'{where}: doc {txt} raw {val:.4f}')
    else: res['bad'].append(f'{where}: doc {txt} raw {val:.4f}')
lines = open('p1alone.md').read().splitlines(); w = None
for l in lines:
    c = [x.strip() for x in l.strip('|').split('|')]
    if not l.startswith('|') or len(c) != 8 or not c[1].isdigit(): continue
    if c[0]: w = c[0]
    k = int(c[1]); a = alone(w, k); a0 = alone(w, 0)
    if c[2] != 'under 0.01': cmp(f'{w} s{k} GB/s', c[2], a['bw'])
    cmp(f'{w} s{k} lat', c[3], a['lat']); cmp(f'{w} s{k} above245', c[4], 100 * (a['lat'] / 245 - 1)); cmp(f'{w} s{k} ips', c[5], a['ips'])
    if k: cmp(f'{w} s{k} vs s0', c[6], 100 * (a['ips'] / a0['ips'] - 1))
    cmp(f'{w} s{k} Mreq/s', c[7], a['rps'])
print('cells OK', res['ok'], '| last-digit', len(res['round']), '| wrong', len(res['bad']))
for x in res['bad']: print('  BAD', x)
for x in res['round']: print('  ROUND', x)
