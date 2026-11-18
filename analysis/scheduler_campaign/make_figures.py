"""Figures of doc 15 (campaign mix results), drawn from the same data as gen_mix.py.
Writes docs/figures/15_victim_vs_worst_1ch.png and docs/figures/15_change_in_highest_slowdown.png."""
import os, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mixdata as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'figures')
os.makedirs(OUT, exist_ok=True)
FIVE = ['tcm', 'atlasr', 'bliss', 'parbs', 'saasm']
HELD = [m for m in range(1, 19) if m not in M.TUNE]
GREY, BLUE, INK, MUTED = '#9aa0a6', '#1f5fbf', '#1f2328', '#59636e'
GOOD, BAD = '#1a7f37', '#cf222e'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})

# 1. victim slowdown against highest slowdown, 15 held-out mixes, 1 channel
fig, axes = plt.subplots(1, 5, figsize=(13, 3.2), sharex=True, sharey=True)
lo, hi = 0.95, 3.0
for ax, s in zip(axes, FIVE):
    for m in HELD:
        a, b = M.metrics(1, 'frfcfs', m), M.metrics(1, s, m)
        ax.plot([a['max'], b['max']], [a['vic'], b['vic']], color=GREY, lw=1, zorder=1)
        ax.scatter([a['max']], [a['vic']], s=26, facecolors='none', edgecolors=GREY, lw=1.2, zorder=2)
        ax.scatter([b['max']], [b['vic']], s=22, color=BLUE, edgecolors='white', lw=0.8, zorder=3)
    ax.plot([lo, hi], [lo, hi], ls='--', lw=0.8, color=MUTED, zorder=0)
    ax.set_title(M.LABEL[s], color=INK, fontsize=10)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.grid(color='#eaeef2', lw=0.6); ax.set_axisbelow(True)
    ax.set_xlabel('Highest slowdown')
axes[0].set_ylabel('Victim slowdown')
axes[0].scatter([], [], s=26, facecolors='none', edgecolors=GREY, label='FR-FCFS')
axes[0].scatter([], [], s=22, color=BLUE, label='scheduler')
axes[0].legend(frameon=False, loc='upper left', fontsize=8)
fig.suptitle('15 held-out mixes, 1 channel: each mix under FR-FCFS (ring) and under the scheduler (dot)', color=INK, fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT, '15_victim_vs_worst_1ch.png'), dpi=160)
plt.close(fig)

# 2. change in highest slowdown from FR-FCFS, per mix, 1 and 2 channels
fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
for ax, ch in zip(axes, (1, 2)):
    mixes = HELD if ch == 1 else range(1, 19)
    for i, s in enumerate(FIVE):
        y = len(FIVE) - 1 - i
        p = [(M.metrics(ch, s, m)['max'] / M.metrics(ch, 'frfcfs', m)['max'] - 1) * 100 for m in mixes]
        ax.scatter(p, [y] * len(p), s=24, color=[GOOD if v < 0 else BAD for v in p], edgecolors='white', lw=0.8, zorder=3)
        md = st.median(p)
        ax.plot([md, md], [y - 0.28, y + 0.28], color=INK, lw=2, zorder=4)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(FIVE))); ax.set_yticklabels([M.LABEL[s] for s in reversed(FIVE)])
    ax.set_xlabel('Change in highest slowdown from FR-FCFS (%)')
    ax.set_title(f'{ch} channel{"s" if ch == 2 else ""}: {len(list(mixes))} mixes', color=INK, fontsize=10)
    ax.grid(axis='x', color='#eaeef2', lw=0.6); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, '15_change_in_highest_slowdown.png'), dpi=160)
plt.close(fig)
print('figures written to', os.path.abspath(OUT))
