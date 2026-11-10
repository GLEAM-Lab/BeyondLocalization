#!/usr/bin/env python3
"""Draw the data figures of the paper into figures/.

Figure screened-reference-touch plots the known-minus-unknown differences of Table tab-reference-success.
Figure frontier-overlap draws the solved-task overlap of the 3 repair systems.
Usage: python analysis/figures.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import boolean, outcome  # noqa: E402
from reproduce import ORACLE_POOLS, SYSTEMS, VIEWS, final_predictions, frequencies, label, pairs  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'figures'


def use_body_font():
    """Use Linux Libertine, the body font of the ACM template, when it is installed."""
    for path in font_manager.findSystemFonts():
        if 'LinLibertine' in path:
            font_manager.fontManager.addfont(path)
    if any('Linux Libertine' in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams.update({'font.family': 'Linux Libertine O', 'mathtext.fontset': 'custom',
                             'mathtext.it': 'Linux Libertine O:italic', 'mathtext.rm': 'Linux Libertine O'})
    plt.rcParams.update({'pdf.fonttype': 42, 'font.size': 10})


def reference_touch():
    rows = []
    for llm, view, m in VIEWS:
        if view == 'non_lite':
            continue
        n = tu = tk = su = sk = 0
        for u, k in pairs(llm, view, m).values():
            if outcome(u) is None or outcome(k) is None or u['touch_g'] == '' or k['touch_g'] == '':
                continue
            n += 1
            tu += u['touch_g'] == '1'
            tk += k['touch_g'] == '1'
            su += outcome(u)
            sk += outcome(k)
        name = label(llm, view).replace(', m=', ', $m$=')
        if llm == 'deepseek' and view == 'lite':
            name += f', $m$={m}'
        rows.append((name, 100 * (tk - tu) / n, 100 * (sk - su) / n))
    rows.reverse()
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    y = range(len(rows))
    ax.axvline(0, color='0.6', lw=0.8)
    ax.scatter([r[1] for r in rows], [i + 0.12 for i in y], marker='o', color='#1f5a96', label='Reference touch', zorder=3)
    ax.scatter([r[2] for r in rows], [i - 0.12 for i in y], marker='s', color='#c4581f', label='Success', zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel('Known minus unknown on the same task pairs (pp)')
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / 'screened-reference-touch.pdf')
    plt.close(fig)


def venn():
    fp = final_predictions()
    solved = {'baseline': [{i for i, r in fp[(s, 'baseline')].items() if boolean(r['resolved'])} for s in SYSTEMS],
              'oracle': [{i for i, r in fp[(s, 'oracle')].items() if boolean(r['resolved'])} for s in SYSTEMS],
              'best_of_k': [{i for i, v in frequencies(ORACLE_POOLS[s]).items() if v > 0} for s in SYSTEMS]}
    colors = ('#1f5a96', '#c4581f', '#3a8a3a')
    centers = ((-0.55, 0.32), (0.55, 0.32), (0.0, -0.62))
    spots = {(1, 0, 0): (-1.05, 0.62), (0, 1, 0): (1.05, 0.62), (0, 0, 1): (0.0, -1.25), (1, 1, 0): (0.0, 0.75),
             (1, 0, 1): (-0.68, -0.38), (0, 1, 1): (0.68, -0.38), (1, 1, 1): (0.0, 0.0)}
    for stem, sets in solved.items():
        fig, ax = plt.subplots(figsize=(2.6, 2.4))
        for (cx, cy), c in zip(centers, colors):
            ax.add_patch(Circle((cx, cy), 1.0, facecolor=c, alpha=0.22, edgecolor=c, lw=1.0))
        for key, (x, yy) in spots.items():
            region = set.intersection(*[sets[i] for i in range(3) if key[i]])
            region -= set().union(*[sets[i] for i in range(3) if not key[i]])
            ax.text(x, yy, str(len(region)), ha='center', va='center', fontsize=10)
        ax.text(-1.25, 1.5, SYSTEMS[0], ha='center', fontsize=10)
        ax.text(1.25, 1.5, SYSTEMS[1], ha='center', fontsize=10)
        ax.text(0.0, -1.85, SYSTEMS[2], ha='center', va='top', fontsize=10)
        ax.set_xlim(-1.8, 1.8)
        ax.set_ylim(-2.05, 1.75)
        ax.set_aspect('equal')
        ax.axis('off')
        fig.savefig(OUT / f'rq3_venn_progression_{stem}.pdf', bbox_inches='tight', pad_inches=0.02)
        plt.close(fig)
        print(f'{stem}: no success on {300 - len(set().union(*sets))} tasks')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    use_body_font()
    reference_touch()
    venn()
