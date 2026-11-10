"""Loading helpers for the release data."""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'
LLMS = ('deepseek', 'qwen', 'glm')
LLM_NAMES = {'deepseek': 'DeepSeek', 'qwen': 'Qwen', 'glm': 'GLM'}


def read(path):
    with open(DATA / path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def boolean(value):
    if value in ('', None):
        return None
    return value.strip().lower() in ('1', 'true', 'yes')


def tasks():
    return {r['instance_id']: r for r in read('tasks.csv')}


def candidate():
    """Candidate responses keyed by (llm, cohort, instance, m, condition)."""
    return {(r['llm'], r['cohort'], r['instance_id'], int(r['m']), r['condition']): r for r in read('candidate/responses.csv')}


def task_sets():
    t = tasks()
    lite = sorted(i for i, r in t.items() if r['in_screened_lite'] == '1')
    verified = sorted(i for i, r in t.items() if r['in_screened_verified'] == '1')
    overlap = sorted(set(lite) & set(verified))
    other = sorted(set(verified) - set(lite))
    non_lite = sorted(i for i in verified if t[i]['in_lite300'] == '0')
    return {'lite': lite, 'verified': verified, 'overlap': overlap, 'other232': other, 'non_lite': non_lite}


def view_rows(rows, llm, view, m):
    """Map each task of a view to its (unknown, known) rows. Verified reuses the Lite rows of the overlap tasks."""
    sets = task_sets()
    ids = sets[view]
    out = {}
    for i in ids:
        cohort = 'C1' if i in sets['lite'] else 'C3'
        out[i] = (rows.get((llm, cohort, i, m, 'unknown')), rows.get((llm, cohort, i, m, 'known')))
    return out


def outcome(row):
    return None if row is None else boolean(row['resolved'])
