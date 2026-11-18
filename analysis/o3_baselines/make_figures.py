"""Figures of docs 10 (O3 alone runs) and 11 (O3 mixed runs), from results/o3_baselines and results/phase1.
Writes five PNG files to docs/figures/."""
import os, sys, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'phase1'))
import o3data as O
import p1common as P

OUT = os.path.join(H, '..', '..', 'docs', 'figures'); os.makedirs(OUT, exist_ok=True)
GREY, BLUE, INK, MUTED, GRID = '#9aa0a6', '#1f5fbf', '#1f2328', '#59636e', '#eaeef2'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})
W = ['tealeaf', 'STREAM', 'fotonik3d', 'streamcluster', 'roms', 'LLM inference',
     'MERCI', 'graph500', 'hnswlib', 'cactus', 'multichase', 'Marian']          # aggressors, then victims
def ips(s, w, ch): return st.mean(O.alone(s, w, k, ch)['ips'] for k in range(4))   # mean of the 4 slots
def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=160); plt.close(fig)
y = list(range(len(W)))[::-1]

# 10a: FR-FCFS instruction rate / FCFS instruction rate - 1, alone, per channel count
fig, ax = plt.subplots(figsize=(7, 4))
for off, ch, col in ((0.18, 1, GREY), (-0.18, 2, BLUE)):
    v = [100 * (ips('frfcfs', w, ch) / ips('fcfs', w, ch) - 1) for w in W]
    ax.barh([t + off for t in y], v, height=0.34, color=col, label=f'{ch} channel{"s" if ch == 2 else ""}')
ax.axvline(0, color=MUTED, lw=0.8); ax.set_yticks(y); ax.set_yticklabels(W)
ax.set_xlabel('FR-FCFS instruction rate vs FCFS, alone (%)'); ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc='lower right'); save(fig, '10_frfcfs_gain_alone.png')

# 10b: instruction rate relative to one FCFS channel, alone
fig, ax = plt.subplots(figsize=(7, 4))
for w, t in zip(W, y):
    b = ips('fcfs', w, 1)
    p = dict(r1=ips('frfcfs', w, 1) / b, f2=ips('fcfs', w, 2) / b, r2=ips('frfcfs', w, 2) / b)
    ax.plot([min(list(p.values()) + [1]), max(list(p.values()) + [1])], [t, t], color=GRID, lw=2, zorder=1)
    ax.scatter(p['r1'], t, s=30, color=GREY, zorder=3, label='FR-FCFS, 1 channel' if t == y[0] else None)
    ax.scatter(p['f2'], t, s=46, facecolors='none', edgecolors=BLUE, lw=1.4, zorder=4, label='FCFS, 2 channels' if t == y[0] else None)
    ax.scatter(p['r2'], t, s=30, color=BLUE, zorder=5, label='FR-FCFS, 2 channels' if t == y[0] else None)
ax.axvline(1, color=INK, lw=1); ax.set_yticks(y); ax.set_yticklabels(W)
ax.set_xlabel('Instruction rate ÷ instruction rate on one FCFS channel, alone')
ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, loc='lower right', fontsize=8)
save(fig, '10_channels_vs_scheduler_alone.png')

# 10c: O3 FCFS alone instruction rate / Phase 1 timing-CPU alone instruction rate, one channel
fig, ax = plt.subplots(figsize=(7, 4))
v = [ips('fcfs', w, 1) / st.mean(P.alone(w, k)['ips'] for k in range(4)) for w in W]
ax.barh(y, v, height=0.6, color=[BLUE if x < 1.2 else GREY for x in v])
for t, x in zip(y, v): ax.text(x + 0.05, t, f'{x:.2f}×', va='center', color=INK, fontsize=8)
ax.axvline(1, color=INK, lw=1); ax.set_yticks(y); ax.set_yticklabels(W)
ax.set_xlabel('O3 instruction rate ÷ Phase 1 (timing CPU) instruction rate, one FCFS channel')
ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True); save(fig, '10_o3_vs_timing_cpu.png')

# 11a: FR-FCFS mix progress / FCFS mix progress - 1, per workload over its mixes
g = {}
for ch in (1, 2):
    for m in range(1, 19):
        a, b = O.mix(m, 'fcfs', ch), O.mix(m, 'frfcfs', ch)
        for i, w in enumerate(a['wl']):
            g.setdefault((w, ch), []).append(100 * (O.prog(b['hosts'][i], w) / O.prog(a['hosts'][i], w) - 1))
fig, ax = plt.subplots(figsize=(7, 4.2))
for off, ch, col in ((0.16, 1, GREY), (-0.16, 2, BLUE)):
    for w, t in zip(W, y):
        v = g[(w, ch)]
        ax.plot([min(v), max(v)], [t + off, t + off], color=col, lw=1.5)
        ax.scatter(st.mean(v), t + off, s=30, color=col, zorder=3, label=(f'{ch} channel{"s" if ch == 2 else ""}' if t == y[0] else None))
ax.axvline(0, color=MUTED, lw=0.8); ax.set_yticks(y); ax.set_yticklabels([w + ('*' if w in O.REQ else '') for w in W])
ax.set_xlabel('FR-FCFS mix progress vs FCFS mix progress (%): mean (dot) and range over its mixes')
ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, loc='lower right')
save(fig, '11_frfcfs_gain_in_mixes.png')

# 11b: highest slowdown per mix in the 4 set-ups, all against each host's 1-channel FCFS alone run
fig, ax = plt.subplots(figsize=(7, 5.2))
ym = list(range(18))[::-1]
for m, t in zip(range(1, 19), ym):
    v = {(s, ch): O.mixmetrics(m, s, ch, 'fcfs', 1)['max'] for s in ('fcfs', 'frfcfs') for ch in (1, 2)}
    ax.plot([min(v.values()), max(v.values())], [t, t], color=GRID, lw=2, zorder=1)
    for (s, ch), x in v.items():
        col = GREY if ch == 1 else BLUE
        lab = f'{"FCFS" if s == "fcfs" else "FR-FCFS"}, {ch} channel{"s" if ch == 2 else ""}' if m == 1 else None
        if s == 'fcfs': ax.scatter(x, t, s=44, facecolors='none', edgecolors=col, lw=1.4, zorder=3, label=lab)
        else: ax.scatter(x, t, s=30, color=col, zorder=4, label=lab)
ax.set_xscale('log'); ax.set_xticks([1, 1.5, 2, 3, 4, 6]); ax.set_xticklabels(['1', '1.5', '2', '3', '4', '6'])
ax.set_yticks(ym); ax.set_yticklabels([f'mix {m}' for m in range(1, 19)])
ax.set_xlabel('Highest slowdown in the mix (Marian left out), against 1-channel FCFS alone runs')
ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, loc='lower right', fontsize=8)
save(fig, '11_highest_slowdown_four_setups.png')
print('figures written to', os.path.abspath(OUT))
