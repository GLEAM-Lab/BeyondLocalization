#!/usr/bin/env python3
"""Recompute the tables of the paper from the CSV files in data/.

Usage: python analysis/reproduce.py [table ...]
Without arguments, every table is printed. Table names follow the paper's LaTeX labels.
"""
import collections
import csv
import statistics
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, LLM_NAMES, boolean, candidate, outcome, read, task_sets, tasks, view_rows  # noqa: E402
from stats import bootstrap_ci_multinomial, holm, mcnemar, paired  # noqa: E402

SYSTEMS = ('Agentless', 'KGCompass', 'ExpeRepair')
ORACLE_POOLS = {'Agentless': 'Agentless-best-patch', 'KGCompass': 'KGCompass-best-patch', 'ExpeRepair': 'ExpeRepair-v1.0-best-patch'}
EVIDENCE_POOLS = {('Agentless', 'KGCompass'): 'Agentless-agentless-kg', ('Agentless', 'ExpeRepair'): 'Agentless-agentless-expe',
                  ('Agentless', 'UnionContext'): 'Agentless-unionprompt', ('ExpeRepair', 'KGCompass'): 'ExpeRepair-experepair-kg',
                  ('ExpeRepair', 'Agentless'): 'ExpeRepair-experepair-agentless', ('ExpeRepair', 'UnionContext'): 'ExpeRepair-unionprompt'}
# The identity views of the paper: 5 main comparisons, then the other Qwen and GLM views.
VIEWS = [('deepseek', 'lite', 10), ('deepseek', 'lite', 20), ('deepseek', 'verified', 20), ('deepseek', 'non_lite', 20),
         ('qwen', 'lite', 20), ('qwen', 'verified', 20), ('qwen', 'non_lite', 20), ('glm', 'lite', 20), ('glm', 'verified', 20),
         ('glm', 'non_lite', 20)]
VIEW_NAMES = {'lite': 'Lite', 'verified': 'Verified', 'non_lite': 'non-Lite', 'other232': '232 other Verified'}
ROWS = candidate()


def pairs(llm, view, m):
    base = 'verified' if view in ('non_lite', 'other232') else view
    rows = view_rows(ROWS, llm, base, m)
    keep = set(task_sets()[view])
    return {i: v for i, v in rows.items() if i in keep}


def label(llm, view, m=None):
    return f'{LLM_NAMES[llm]} / {VIEW_NAMES[view]}' + (f', m={m}' if m is not None else '')


def tested(row):
    return row is not None and row['stage'] == 'tested'


def frequencies(name):
    with open(DATA / 'system/sample_frequencies' / f'{name}.csv', encoding='utf-8-sig') as f:
        return {r['instance_id']: int(r['resolved_in_samples']) for r in csv.DictReader(f)}


def expected(freq, k):
    return sum(1 - comb(10 - s, k) / comb(10, k) for s in freq.values())


def fmt_ci(ci):
    return f'[{ci[0]:.1f},{ci[1]:.1f}]'


def tab_candidate_outcomes():
    print('Table tab-candidate-outcomes: resolved / scored and success rate')
    cells = [('deepseek', 'lite', m, c) for m, c in ((0, 'unknown'), (10, 'unknown'), (10, 'known'), (20, 'unknown'), (20, 'known'))]
    cells += [(llm, v, 20, c) for llm in ('qwen', 'glm') for v in ('lite', 'verified') for c in ('unknown', 'known')]
    cells += [('deepseek', 'verified', 20, c) for c in ('unknown', 'known')]
    for llm, view, m, cond in cells:
        values = [outcome(u if cond == 'unknown' else k) for u, k in pairs(llm, view, m).values()]
        scored = [v for v in values if v is not None]
        print(f'  {label(llm, view, m):28s} {cond[0].upper()}  {sum(scored)} / {len(scored)}  {100 * sum(scored) / len(scored):.1f}')


def tab_count_contrasts():
    print('Table tab-count-contrasts: DeepSeek unknown prompts on Lite, second minus first')
    runs = {m: {i: outcome(u) for i, (u, _) in pairs('deepseek', 'lite', m).items()} for m in (0, 10, 20)}
    for a, b in ((0, 10), (0, 20), (10, 20)):
        r = paired(runs[a], runs[b])
        print(f'  m={a} vs m={b}: pairs {r["pairs"]}, first only {r["a_only"]}, second only {r["b_only"]}, '
              f'{r["diff_pp"]:+.1f} {fmt_ci(r["ci_pp"])} p={r["p"]:.3f}')
    joint = [i for i in runs[0] if all(runs[m].get(i) is not None for m in (0, 10, 20))]
    print(f'  jointly scored {len(joint)}: resolved {[sum(runs[m][i] for i in joint) for m in (0, 10, 20)]}, '
          f'union {sum(any(runs[m][i] for m in (0, 10, 20)) for i in joint)}')


def identity(llm, view, m):
    p = pairs(llm, view, m)
    return paired({i: outcome(u) for i, (u, k) in p.items()}, {i: outcome(k) for i, (u, k) in p.items()})


def tab_identity_effects():
    print('Table tab-identity-effects: known minus unknown on complete pairs')
    first = []
    second = []
    for llm, view, m in VIEWS + [('deepseek', 'other232', 20)]:
        r = identity(llm, view, m)
        print(f'  {label(llm, view, m):32s} pairs {r["pairs"]} K-only {r["b_only"]} U-only {r["a_only"]} '
              f'{r["diff_pp"]:+.1f} {fmt_ci(r["ci_pp"])} p={r["p"]:.3f}')
        (first if (llm == 'deepseek' or (llm, view) == ('qwen', 'lite')) else second).append(r['p'])
    counts = [paired({i: outcome(u) for i, (u, _) in pairs('deepseek', 'lite', a).items()},
                     {i: outcome(u) for i, (u, _) in pairs('deepseek', 'lite', b).items()})['p'] for a, b in ((0, 10), (0, 20), (10, 20))]
    for llm in ('qwen', 'glm'):
        second.append(identity(llm, 'other232', 20)['p'])
    print(f'  Holm family 1, 9 tests, smallest adjusted p {min(holm(first + counts)):.3f}')
    print(f'  Holm family 2, 7 tests, smallest adjusted p {min(holm(second)):.3f}')


def tab_loop_counts():
    print('Table tab-loop-counts: DeepSeek responses that end at the length limit')
    for view, m in (('lite', 10), ('lite', 20), ('other232', 20)):
        p = pairs('deepseek', view, m)
        loops = {c: sum(1 for u, k in p.values() if (u if c == 0 else k) and (u if c == 0 else k)['finish_reason'] == 'length') for c in (0, 1)}
        resp = {c: sum(1 for u, k in p.values() if (u if c == 0 else k) and (u if c == 0 else k)['finish_reason']) for c in (0, 1)}
        print(f'  {VIEW_NAMES[view]}, m={m}: U {loops[0]} / {resp[0]}, K {loops[1]} / {resp[1]}, '
              f'success {identity("deepseek", view, m)["diff_pp"]:+.1f}')


def tab_stage_transitions():
    print('Table tab-stage-transitions: wins split by whether the losing response reached the tests')
    for llm, view, m in VIEWS:
        st = collections.Counter()
        complete = 0
        for u, k in pairs(llm, view, m).values():
            ou, ok = outcome(u), outcome(k)
            if ou is None or ok is None:
                continue
            complete += 1
            if ok and not ou:
                st['K_U_tested' if tested(u) else 'K_U_untested'] += 1
            if ou and not ok:
                st['U_K_tested' if tested(k) else 'U_K_untested'] += 1
        print(f'  {label(llm, view, m):32s} pairs {complete}: K-only {st["K_U_tested"]}/{st["K_U_untested"]}, '
              f'U-only {st["U_K_tested"]}/{st["U_K_untested"]}  (loser tested/untested)')


def touch(row):
    return None if row is None else boolean(row['touch_g'])


def tab_reference_success():
    print('Table tab-reference-success: reference touch and success on common pairs, and the decomposition of the effect')
    for llm, view, m in VIEWS:
        if view == 'non_lite':
            continue
        groups = collections.defaultdict(lambda: [0, 0, 0])
        ref = [0, 0, 0, 0, 0]
        complete = 0
        for u, k in pairs(llm, view, m).values():
            ou, ok = outcome(u), outcome(k)
            if ou is None or ok is None:
                continue
            complete += 1
            tu, tk = touch(u), touch(k)
            if tu is None or tk is None:
                g = 'mapping_unknown'
            else:
                g = 'both' if tu and tk else 'known_only' if tk else 'unknown_only' if tu else 'neither'
                ref = [ref[0] + 1, ref[1] + tu, ref[2] + tk, ref[3] + ou, ref[4] + ok]
            groups[g][0] += 1
            groups[g][1] += ok
            groups[g][2] += ou
        contrib = {g: 100 * (v[1] - v[2]) / complete for g, v in groups.items()}
        print(f'  {label(llm, view, m):28s} pairs {ref[0]} touch {ref[1]} / {ref[2]} success {ref[3]} / {ref[4]}; '
              f'known-only {contrib.get("known_only", 0):+.1f} both {contrib.get("both", 0):+.1f}')


def tab_discordant_sets():
    print('Table tab-discordant-sets: edit sets of the final patches in pairs whose outcomes differ')
    for llm, view, m in VIEWS:
        d = same = every = exact = files = 0
        for u, k in pairs(llm, view, m).values():
            ou, ok = outcome(u), outcome(k)
            if ou is None or ok is None or ou == ok:
                continue
            d += 1
            files += bool(k['files'] and u['files'] and set(k['files'].split(';')) == set(u['files'].split(';')))
            if k['g_edited'] and k['g_edited'] == u['g_edited']:
                same += 1
                if k['touch_all_g'] == '1' and u['touch_all_g'] == '1':
                    every += 1
                    exact += k['outside_g'] == '0' and u['outside_g'] == '0'
        print(f'  {label(llm, view, m):32s} pairs {d} same G {same} all G {every} exactly G {exact} same files {files}')


def tab_candidate_composition():
    print('Table tab-candidate-composition: distractor touch of unknown-condition patches and the mixed-minus-same-file interaction')
    comp = collections.defaultdict(dict)
    for r in read('candidate/composition.csv'):
        comp[(r['llm'], r['view'], int(r['m']))][r['instance_id']] = r['file_stratum']
    names = {'lite': 'Lite181', 'verified': 'Verified274', 'non_lite': 'Verified_nonoverlap222'}
    for llm, view, m in VIEWS[:5]:
        p = pairs(llm, view, m)
        usable = [u for u, _ in p.values() if u is not None and u['distractor_touch'] != '']
        nonempty = [u for u in usable if u['nonempty_patch'] == '1']
        touched = sum(u['distractor_touch'] == '1' for u in usable)
        strata = comp[(llm, names[view], m)]
        d = {s: [int(outcome(k)) - int(outcome(u)) for i, (u, k) in p.items()
                 if strata.get(i) == s and outcome(u) is not None and outcome(k) is not None] for s in ('all_same_file', 'mixed_files')}
        import numpy as np
        rng = np.random.default_rng(20261024)

        def draws(values):
            v = np.asarray(values, dtype=float)
            uniq, cnt = np.unique(v, return_counts=True)
            return rng.multinomial(len(v), cnt / cnt.sum(), size=10000) @ uniq / len(v)
        diff = draws(d['mixed_files']) - draws(d['all_same_file'])
        lo, hi = np.quantile(diff, [.025, .975])
        effect = sum(d['mixed_files']) / len(d['mixed_files']) - sum(d['all_same_file']) / len(d['all_same_file'])
        print(f'  {label(llm, view, m):32s} touch {touched}/{len(usable)} and {touched}/{len(nonempty)}, '
              f'interaction {100 * effect:+.1f} [{100 * lo:.1f},{100 * hi:.1f}]')


def tab_issue_strata():
    print('Table tab-issue-strata: identity effect by whether the issue names the developer-modified functions')
    t = tasks()
    for llm, view, m in VIEWS[:5]:
        p = pairs(llm, view, m)
        out = []
        for level in ('full', 'none'):
            sub = {i: v for i, v in p.items() if t[i]['issue_names_target'] == level}
            d = [int(outcome(k)) - int(outcome(u)) for u, k in sub.values() if outcome(u) is not None and outcome(k) is not None]
            ci = bootstrap_ci_multinomial(d)
            out.append(f'{level}: pairs {len(d)} {100 * sum(d) / len(d):+.1f} [{100 * ci[0]:.1f},{100 * ci[1]:.1f}]')
        print(f'  {label(llm, view, m):32s} ' + '; '.join(out))
    lite = task_sets()['lite']
    counts = collections.Counter(t[i]['issue_names_target'] for i in lite)
    ver = collections.Counter(t[i]['issue_names_target'] for i in task_sets()['verified'])
    print(f'  Lite strata {dict(counts)}; Verified strata {dict(ver)}')


def tab_native_candidates():
    print('Tables tab-native-candidate-outcomes and tab-native-candidate-effects')
    rows = read('native/responses.csv')
    by = collections.defaultdict(dict)
    cover = {}
    for r in rows:
        by[r['condition']][r['instance_id']] = boolean(r['resolved'])
        cover[r['instance_id']] = r['coverage']
    for c in 'ABC':
        s = sum(bool(v) for v in by[c].values())
        print(f'  {c}: success {s}, unsuccessful {len(by[c]) - s}, {100 * s / len(by[c]):.1f}%')
    groups = {'Missing G': [i for i, c in cover.items() if c != 'covered'], 'All': list(cover),
              'Covered G': [i for i, c in cover.items() if c == 'covered'], 'Complete miss': [i for i, c in cover.items() if c == 'all_miss'],
              'Partial miss': [i for i, c in cover.items() if c == 'partial_miss']}
    for a, b, g in (('A', 'B', 'Missing G'), ('B', 'C', 'All'), ('B', 'C', 'Covered G'), ('B', 'C', 'Missing G'),
                    ('A', 'B', 'Complete miss'), ('A', 'B', 'Partial miss')):
        ids = groups[g]
        r = paired({i: by[a][i] for i in ids}, {i: by[b][i] for i in ids})
        print(f'  {a}/{b} {g}: pairs {r["pairs"]} second only {r["b_only"]} first only {r["a_only"]} '
              f'{r["diff_pp"]:+.1f} {fmt_ci(r["ci_pp"])} p={r["p"]:.3f}')
    native = read('native/responses.csv')
    print('  final patches touching G: ' + ', '.join(f'{c} {sum(r["final_gt_any"] == "true" for r in native if r["condition"] == c)}' for c in 'ABC'))


def tab_agent():
    print('Tables tab-agent-outcomes and tab-agent-effects')
    runs = read('agent/runs.csv')
    for llm in ('qwen', 'glm'):
        by = {c: {r['instance_id']: r for r in runs if r['llm'] == llm and r['condition'] == c} for c in ('unmarked', 'marked')}
        for c, rs in by.items():
            vals = list(rs.values())
            steps = [int(r['first_target_file_step']) for r in vals if r['first_target_file_step'] not in ('', 'None')]
            print(f'  {LLM_NAMES[llm]} {c}: resolved {sum(boolean(r["resolved"]) for r in vals)}, '
                  f'diff submitted {sum(r["submission_kind"] == "diff" for r in vals)}, names a G file {len(steps)}, '
                  f'first G step {statistics.median(steps):g}, LLM calls {statistics.median(int(r["n_calls"]) for r in vals):g}, '
                  f'step limit without submission {sum(r["exit_status"] == "LimitsExceeded" and r["submission_kind"] != "diff" for r in vals)}')
        def value(r, field):
            if field == 'working_tree':
                return boolean(r['worktree_resolved'] or r['resolved'])
            return boolean(r[field])
        for field in ('resolved', 'working_tree', 'touch_g'):
            a = {i: value(r, field) for i, r in by['unmarked'].items()}
            b = {i: value(r, field) for i, r in by['marked'].items()}
            r = paired(a, b)
            print(f'    {field}: pairs {r["pairs"]} M-only {r["b_only"]} U-only {r["a_only"]} {r["diff_pp"]:+.1f} '
                  f'{fmt_ci(r["ci_pp"])} p={r["p"]:.3f}')
        only = [i for i, r in by['marked'].items() if boolean(r['resolved']) and not boolean(by['unmarked'][i]['resolved'])]
        limit = sum(by['unmarked'][i]['exit_status'] == 'LimitsExceeded' for i in only)
        print(f'    marked-only successes {len(only)}, of which the unmarked run hit the step limit {limit}')


def final_predictions():
    out = collections.defaultdict(dict)
    for r in read('system/final_predictions.csv'):
        out[(r['system'], r['config'])][r['instance_id']] = r
    return out


def tab_oracle_main():
    print('Table tab-oracle-main and tab-baseline-span: final predictions on the 300 Lite tasks')
    fp = final_predictions()
    for s in SYSTEMS:
        for cfg in ('baseline', 'oracle'):
            rows = list(fp[(s, cfg)].values())
            res = sum(boolean(r['resolved']) for r in rows)
            comp = sum(boolean(r['completed']) for r in rows)
            print(f'  {s} {cfg}: resolved {res} ({100 * res / len(rows):.1f}), completed {100 * comp / len(rows):.1f}, '
                  f'pass among completed {100 * res / comp:.1f}')
        hit = [i for i, r in fp[(s, 'baseline')].items() if r['oracle_rank'] and float(r['oracle_rank']) < 9999]
        b = sum(boolean(fp[(s, 'baseline')][i]['resolved']) for i in hit)
        o = sum(boolean(fp[(s, 'oracle')][i]['resolved']) for i in hit)
        print(f'    span hit {len(hit)}: baseline {b} ({100 * b / len(hit):.1f}), oracle {o} ({100 * o / len(hit):.1f})')


def tab_samples():
    print('Tables tab-selection-summary and tab-success-frequency: 10-sample Oracle pools')
    lite = set(task_sets()['lite'])
    fp = final_predictions()
    for s in SYSTEMS:
        f = frequencies(ORACLE_POOLS[s])
        sub = {i: v for i, v in f.items() if i in lite}
        bins = [sum(v == 0 for v in f.values()), sum(1 <= v <= 4 for v in f.values()), sum(5 <= v <= 9 for v in f.values()), sum(v == 10 for v in f.values())]
        final = {i: boolean(r['resolved']) for i, r in fp[(s, 'oracle')].items()}
        missed = sum(1 for i, v in f.items() if v > 0 and not final[i])
        low = [i for i, v in f.items() if 1 <= v <= 4]
        print(f'  {s}: 300 expected5 {expected(f, 5):.1f} solved10 {sum(v > 0 for v in f.values())}; '
              f'181 expected5 {expected(sub, 5):.1f} solved10 {sum(v > 0 for v in sub.values())}')
        print(f'    bins 0/1-4/5-9/10 {bins}, expected1 {expected(f, 1):.1f}, final {sum(final.values())}, '
              f'pool success but final failure {missed}, final success on 1-4 tasks {sum(final[i] for i in low)} of {len(low)}')


def tab_shared_prompt():
    print('Table tab-oracle-common-wrapper: shared-prompt Solved@10 counts')
    for r in read('system/shared_prompt.csv'):
        print(f'  {r["system"]}: native {round(3 * float(r["C_shared_wrapper_native_loc_percent"]))}, '
              f'oracle {round(3 * float(r["D_shared_wrapper_oracle_loc_percent"]))}, shared builder {round(3 * float(r["E_shared_builder_oracle_shared_wrapper_percent"]))}')


def tab_evidence():
    print('Table tab-evidence-transfer: Solved@10 of added evidence and its controls')
    for r in read('system/evidence_controls.csv'):
        print(f'  {r["wrapper"]} {r["condition"]}: added {float(r["solved_at_k_percent"]):.1f}, filler {float(r["exact_filler_solved_at_k_percent"]):.1f} '
              f'(Holm p {r["exact_filler_holm_family"]}), wrong {float(r["hard_negative_solved_at_k_percent"]):.1f} '
              f'(Holm p {r["hard_negative_holm_family"]}), prompt tokens {float(r["mean_prompt_ktokens"]):.2f}k')

    print('Filler and wrong-evidence controls on the 300 Lite tasks and on the 181 screened tasks (Holm over the 6 conditions of each control)')
    cond_pool = {'agentless_kg': 'Agentless-agentless-kg', 'agentless_expe': 'Agentless-agentless-expe', 'agentless_union': 'Agentless-unionprompt',
                 'experepair_kg': 'ExpeRepair-experepair-kg', 'experepair_agentless': 'ExpeRepair-experepair-agentless', 'experepair_union': 'ExpeRepair-unionprompt'}
    ctrl_pool = {'agentless_kg': 'Agentless-agentless-kg', 'agentless_expe': 'Agentless-agentless-expe', 'agentless_union': 'Agentless-agentless-union',
                 'experepair_kg': 'ExpeRepair-experepair-kg', 'experepair_agentless': 'ExpeRepair-experepair-agentless', 'experepair_union': 'ExpeRepair-experepair-union'}
    rows = read('system/evidence_controls.csv')
    screened = set(task_sets()['lite'])
    for label_, keep in (('300 Lite tasks', None), ('181 screened tasks', screened)):
        print(f'  {label_}')
        for kind, suffix in (('filler', 'exact-filler'), ('wrong evidence', 'irrelevant-hn')):
            stats = []
            for r in rows:
                cond = frequencies(cond_pool[r['condition_key']])
                ctrl = frequencies(ctrl_pool[r['condition_key']] + '-' + suffix)
                ids = [i for i in cond if keep is None or i in keep]
                wins = sum(cond[i] > 0 and ctrl[i] == 0 for i in ids)
                losses = sum(cond[i] == 0 and ctrl[i] > 0 for i in ids)
                stats.append((r, 100 * sum(cond[i] > 0 for i in ids) / len(ids), 100 * sum(ctrl[i] > 0 for i in ids) / len(ids), wins, losses))
            adjusted = holm([mcnemar(w, l) for _, _, _, w, l in stats])
            for (r, c, f, w, l), a in zip(stats, adjusted):
                print(f'    {kind}, {r["wrapper"]} {r["condition"]}: added {c:.1f}, control {f:.1f}, added-only {w}, control-only {l}, Holm p {a:.2g}')
    print('Tables tab-evidence-split-budget, tab-evidence-trajectory, and tab-rq4-win-frontier-gap')
    native = {s: frequencies(ORACLE_POOLS[s]) for s in SYSTEMS}
    union = {i for s in SYSTEMS for i, v in native[s].items() if v > 0}
    for s, (x, y) in (('Agentless', ('KGCompass', 'ExpeRepair')), ('ExpeRepair', ('KGCompass', 'Agentless'))):
        fa, fb, fu = frequencies(EVIDENCE_POOLS[(s, x)]), frequencies(EVIDENCE_POOLS[(s, y)]), frequencies(EVIDENCE_POOLS[(s, 'UnionContext')])
        split = sum(1 - comb(10 - fa[i], 5) * comb(10 - fb[i], 5) / comb(10, 5) ** 2 for i in fa)
        print(f'  {s}: expected 5+5 {split:.1f}, observed UnionContext {sum(v > 0 for v in fu.values())}, '
              f'difference {100 * (split - sum(v > 0 for v in fu.values())) / 300:+.1f} pp')
        fk = frequencies(EVIDENCE_POOLS[(s, 'KGCompass')])
        print(f'    KGCompass evidence solved10 {sum(v > 0 for v in fk.values())} all10 {sum(v == 10 for v in fk.values())}; '
              f'UnionContext solved10 {sum(v > 0 for v in fu.values())} all10 {sum(v == 10 for v in fu.values())}; '
              f'all10 KG to partial Union {sum(1 for i in fk if fk[i] == 10 and 0 < fu[i] < 10)}, reverse {sum(1 for i in fk if fu[i] == 10 and 0 < fk[i] < 10)}')
        base = native[s]
        for ctx in (x, y, 'UnionContext'):
            f = frequencies(EVIDENCE_POOLS[(s, ctx)])
            wins = [i for i in f if f[i] > 0 and base[i] == 0]
            losses = [i for i in f if f[i] == 0 and base[i] > 0]
            frontier = [i for i in wins if i not in union]
            print(f'    {ctx}: wins {len(wins)} losses {len(losses)} in native union {len(wins) - len(frontier)} '
                  f'frontier {len(frontier)} ({100 * len(frontier) / len(wins):.1f}%)')
    reached = {i for (s, ctx), name in EVIDENCE_POOLS.items() for i, v in frequencies(name).items() if v > 0 and i not in union}
    print(f'  tasks with no recorded success in the 3 Oracle pools: {300 - len(union)}; reached by any added evidence: {len(reached)}')


def _pair_line(label, u, k):
    r = paired(u, k)
    return f'  {label}: pairs {r["pairs"]}, known-only {r["b_only"]}, unknown-only {r["a_only"]}, diff {r["diff_pp"]:+.1f} pp, p {r["p"]:.3f}'


def _rows(path, **keys):
    return [r for r in read(path) if all(r[k] == v for k, v in keys.items())]


def tab_robustness():
    print('Robustness checks: bounded DeepSeek output (R1), repeated Qwen sampling (R2), and prompt variants (R3)')
    print('R1: DeepSeek Lite, max_tokens 8192, known minus unknown')
    r1 = read('robustness/r1_deepseek_bounded.csv')
    for m in ('10', '20'):
        sub = [r for r in r1 if r['m'] == m]
        u = {r['instance_id']: boolean(r['resolved']) for r in sub if r['condition'] == 'unknown'}
        k = {r['instance_id']: boolean(r['resolved']) for r in sub if r['condition'] == 'known'}
        touch = {c: sum(r['touch_g'] == '1' for r in sub if r['condition'] == c) for c in ('unknown', 'known')}
        length = {c: sum(r['finish_reason'] == 'length' for r in sub if r['condition'] == c) for c in ('unknown', 'known')}
        print(_pair_line(f'm={m}', u, k) + f'; touch G unknown {touch["unknown"]} known {touch["known"]}; length unknown {length["unknown"]} known {length["known"]}')
    print('R2: Qwen, 60 Lite tasks, m=20; repeat 0 is the original temperature-0 response, repeats 1 to 4 sample at temperature 0.2')
    r2 = read('robustness/r2_qwen_repeats.csv')
    ids = sorted({r['instance_id'] for r in r2})
    base = {(r['instance_id'], r['condition']): boolean(r['resolved']) for r in read('candidate/responses.csv')
            if r['llm'] == 'qwen' and r['cohort'] == 'C1' and r['m'] == '20' and r['instance_id'] in ids}
    print(_pair_line('repeat 0', {i: base.get((i, 'unknown')) for i in ids}, {i: base.get((i, 'known')) for i in ids}))
    for rep in sorted({r['repeat'] for r in r2}):
        sub = [r for r in r2 if r['repeat'] == rep]
        u = {r['instance_id']: boolean(r['resolved']) for r in sub if r['condition'] == 'unknown'}
        k = {r['instance_id']: boolean(r['resolved']) for r in sub if r['condition'] == 'known'}
        print(_pair_line(f'repeat {rep}', u, k) + f'; solved unknown {sum(v is True for v in u.values())} known {sum(v is True for v in k.values())}')
    print('R3: Lite 181 tasks, m=20; variants a (location sentence), b (function list), c (neutral sentence) against the existing prompts')
    r3 = read('robustness/r3_variants.csv')
    for llm in ('qwen', 'glm'):
        old = {(r['instance_id'], r['condition']): r for r in read('candidate/responses.csv')
               if r['llm'] == llm and r['cohort'] == 'C1' and r['m'] == '20'}
        tid = sorted({i for i, _ in old})
        print(f'  {LLM_NAMES[llm]} existing prompts: touch G unknown {sum(old[(i, "unknown")]["touch_g"] == "1" for i in tid)} '
              f'known {sum(old[(i, "known")]["touch_g"] == "1" for i in tid)} of {len(tid)}')
        for v in 'abc':
            sub = {r['instance_id']: r for r in r3 if r['llm'] == llm and r['condition'] == v}
            res = {i: boolean(sub[i]['resolved']) for i in tid if i in sub}
            for ref in ('unknown', 'known'):
                rr = {i: boolean(old[(i, ref)]['resolved']) for i in tid}
                print(_pair_line(f'{LLM_NAMES[llm]} variant {v} minus {ref}', rr, res)
                      + (f'; touch G {sum(r["touch_g"] == "1" for r in sub.values())} of {len(sub)}' if ref == 'unknown' else ''))


def tab_statement_overlap():
    print('Statement-level overlap of the final patches in known/unknown pairs that differ in outcome and edit the same developer-modified functions')
    rows = read('candidate/statement_overlap.csv')
    views = []
    for r in rows:
        key = (r['llm'], r['view'], int(r['m']))
        if key not in views:
            views.append(key)

    def line(label, sub):
        c = collections.Counter(r['category'] for r in sub)
        win = [r['known_hits_dev' if r['winner'] == 'known' else 'unknown_hits_dev'] for r in sub]
        lose = [r['unknown_hits_dev' if r['winner'] == 'known' else 'known_hits_dev'] for r in sub]
        win, lose = [x for x in win if x], [x for x in lose if x]
        print(f'  {label}: pairs {len(sub)}, same statements {c["same"]}, overlapping {c["overlap"]}, disjoint {c["disjoint"]}, unmapped {c["unmapped"]}; '
              f'winner hits a developer statement {win.count("1")} of {len(win)}, loser {lose.count("1")} of {len(lose)}')
    for key in sorted(views, key=lambda k: VIEWS.index(k) if k in VIEWS else 99):
        line(label(*key), [r for r in rows if (r['llm'], r['view'], int(r['m'])) == key])
    disjoint = [r for r in rows if r['view'] != 'verified']
    line('pooled over the non-overlapping views (Lite and non-Lite)', disjoint)
    same = [r for r in disjoint if r['category'] == 'same']
    print(f'  among {len(same)} pairs with the same statements, the 2 patches are identical in {sum(r["identical_patch"] == "1" for r in same)} pairs; all others differ in the code written there')


def tab_output_tail():
    print('Table tab-output-tail: DeepSeek completion reasons')
    rows = [r for r in ROWS.values() if r['llm'] == 'deepseek' and r['finish_reason']]
    for reason in ('stop', 'length'):
        sub = [r for r in rows if r['finish_reason'] == reason]
        res = sum(r['resolved'] == '1' for r in sub)
        print(f'  {reason}: responses {len(sub)}, resolved {res}, unresolved {len(sub) - res}, output tokens {sum(int(r["output_tokens"]) for r in sub)}')
    stages = collections.Counter(r['stage'] for r in rows)
    loops = [r for r in rows if r['finish_reason'] == 'length']
    print(f'  stages {dict(stages)}; loops without a testable patch {sum(r["stage"] != "tested" for r in loops)}')


def tab_failure_causes():
    print('Table tab-failure-causes: LLM labels of 257 failed responses')
    labels = collections.Counter(r['label'] for r in read('failure_labels.csv'))
    total = sum(labels.values())
    for k, v in labels.most_common():
        print(f'  {k}: {v} ({100 * v / total:.1f}%)')


TABLES = {'candidate-outcomes': tab_candidate_outcomes, 'count-contrasts': tab_count_contrasts, 'identity-effects': tab_identity_effects,
          'loop-counts': tab_loop_counts, 'stage-transitions': tab_stage_transitions, 'reference-success': tab_reference_success,
          'discordant-sets': tab_discordant_sets, 'candidate-composition': tab_candidate_composition, 'issue-strata': tab_issue_strata,
          'native-candidates': tab_native_candidates, 'agent': tab_agent, 'oracle-main': tab_oracle_main, 'samples': tab_samples,
          'shared-prompt': tab_shared_prompt, 'evidence': tab_evidence, 'robustness': tab_robustness, 'statement-overlap': tab_statement_overlap, 'output-tail': tab_output_tail, 'failure-causes': tab_failure_causes}

if __name__ == '__main__':
    for name in sys.argv[1:] or TABLES:
        TABLES[name]()
        print()
