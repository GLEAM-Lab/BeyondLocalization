#!/usr/bin/env python3
"""Print the 181-task rows of Tables 14, 15, 17, and 19 and the 181-task RQ4 counts.

The system experiments ran on the 300 Lite tasks. This script restricts their outcomes to the 181 screened Lite tasks.
Usage: python analysis/screened_subset.py
"""
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import boolean, task_sets  # noqa: E402
from reproduce import EVIDENCE_POOLS, ORACLE_POOLS, SYSTEMS, final_predictions, frequencies  # noqa: E402

lite = set(task_sets()['lite'])
n = len(lite)
fp = final_predictions()
print(f'Tasks: {n}')
print('\nTable 14 on the subset: final predictions')
for s in SYSTEMS:
    for cfg in ('baseline', 'oracle'):
        rows = [r for i, r in fp[(s, cfg)].items() if i in lite]
        res = sum(boolean(r['resolved']) for r in rows)
        comp = sum(boolean(r['completed']) for r in rows)
        print(f'  {s:10s} {cfg:8s} resolved {res} ({100 * res / n:.1f}%), completed {100 * comp / n:.1f}%, pass among completed {100 * res / comp:.1f}%')
print('\nTable 15 on the subset: tasks whose Baseline localization reaches G')
for s in SYSTEMS:
    hit = [i for i, r in fp[(s, 'baseline')].items() if i in lite and r['oracle_rank'] and float(r['oracle_rank']) < 9999]
    b = sum(boolean(fp[(s, 'baseline')][i]['resolved']) for i in hit)
    o = sum(boolean(fp[(s, 'oracle')][i]['resolved']) for i in hit)
    print(f'  {s:10s} tasks {len(hit)}, Baseline {b} ({100 * b / len(hit):.1f}%), Oracle {o} ({100 * o / len(hit):.1f}%)')
print('\nTable 17 on the subset: success counts of the 10-sample Oracle pools')
for s in SYSTEMS:
    f = {i: v for i, v in frequencies(ORACLE_POOLS[s]).items() if i in lite}
    bins = [sum(v == 0 for v in f.values()), sum(1 <= v <= 4 for v in f.values()), sum(5 <= v <= 9 for v in f.values()), sum(v == 10 for v in f.values())]
    final = {i: boolean(r['resolved']) for i, r in fp[(s, 'oracle')].items() if i in lite}
    e1 = sum(1 - comb(10 - v, 1) / comb(10, 1) for v in f.values())
    e5 = sum(1 - comb(10 - v, 5) / comb(10, 5) for v in f.values())
    missed = sum(1 for i, v in f.items() if v > 0 and not final[i])
    print(f'  {s:10s} 0/1-4/5-9/10 {bins}, Solved@10 {sum(v > 0 for v in f.values())}, expected 5 {e5:.1f}, expected 1 {e1:.1f}, '
          f'final {sum(final.values())}, pool success but final failure {missed}')
print('\nTables 18 to 20 on the subset: added evidence (Solved@10)')
native = {s: {i: v for i, v in frequencies(ORACLE_POOLS[s]).items() if i in lite} for s in SYSTEMS}
union = {i for s in SYSTEMS for i, v in native[s].items() if v > 0}
for s, (x, y) in (('Agentless', ('KGCompass', 'ExpeRepair')), ('ExpeRepair', ('KGCompass', 'Agentless'))):
    base = native[s]
    print(f'  {s} native {sum(v > 0 for v in base.values())} ({100 * sum(v > 0 for v in base.values()) / n:.1f}%)')
    for ctx in (x, y, 'UnionContext'):
        f = {i: v for i, v in frequencies(EVIDENCE_POOLS[(s, ctx)]).items() if i in lite}
        wins = [i for i in f if f[i] > 0 and base[i] == 0]
        losses = [i for i in f if f[i] == 0 and base[i] > 0]
        frontier = [i for i in wins if i not in union]
        print(f'    + {ctx:12s} {sum(v > 0 for v in f.values())} ({100 * sum(v > 0 for v in f.values()) / n:.1f}%), wins {len(wins)}, losses {len(losses)}, frontier wins {len(frontier)}')
    fa = {i: v for i, v in frequencies(EVIDENCE_POOLS[(s, x)]).items() if i in lite}
    fb = {i: v for i, v in frequencies(EVIDENCE_POOLS[(s, y)]).items() if i in lite}
    fu = {i: v for i, v in frequencies(EVIDENCE_POOLS[(s, 'UnionContext')]).items() if i in lite}
    split = sum(1 - comb(10 - fa[i], 5) * comb(10 - fb[i], 5) / comb(10, 5) ** 2 for i in fa)
    print(f'    split 5+5 expected {split:.1f} vs UnionContext {sum(v > 0 for v in fu.values())}')
reached = {i for name in EVIDENCE_POOLS.values() for i, v in frequencies(name).items() if i in lite and v > 0 and i not in union}
print(f'\nRQ4 on the subset: no recorded success in the 3 Oracle pools {n - len(union)}, reached by added evidence {len(reached)}')
for cfg in ('baseline', 'oracle'):
    sol = {i for s in SYSTEMS for i, r in fp[(s, cfg)].items() if i in lite and boolean(r['resolved'])}
    print(f'  Figure 3 {cfg}: no success on {n - len(sol)}')
