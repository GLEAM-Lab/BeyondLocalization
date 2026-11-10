"""Paired statistics used in the paper: exact McNemar tests, task bootstrap intervals, and Holm adjustment."""
import math
import random

SEED = 20261024
ITERATIONS = 10000


def mcnemar(wins, losses):
    """Exact two-sided McNemar test on the discordant counts."""
    n = wins + losses
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2 ** n)


def bootstrap_ci(diffs, iterations=ITERATIONS, seed=SEED):
    """Percentile 95% interval of the mean task difference, resampling tasks with replacement."""
    n = len(diffs)
    if not any(diffs):
        return 0.0, 0.0
    rng = random.Random(seed)
    boot = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(iterations))
    return boot[int(.025 * (iterations - 1))], boot[int(.975 * (iterations - 1))]


def bootstrap_ci_multinomial(diffs, iterations=ITERATIONS, seed=SEED):
    """The same task bootstrap drawn as multinomial counts over the distinct differences."""
    import numpy as np
    values = np.asarray(diffs, dtype=float)
    unique, counts = np.unique(values, return_counts=True)
    weights = np.random.default_rng(seed).multinomial(len(values), counts / counts.sum(), size=iterations)
    draws = weights @ unique / len(values)
    lo, hi = np.quantile(draws, [.025, .975])
    return float(lo), float(hi)


def paired(a, b, multinomial=False):
    """Compare outcome maps a and b, task id to bool or None, on the tasks where both are observed."""
    tasks = sorted(t for t in a if t in b and a[t] is not None and b[t] is not None)
    diffs = [int(b[t]) - int(a[t]) for t in tasks]
    wins = sum(d == 1 for d in diffs)
    losses = sum(d == -1 for d in diffs)
    ci = (bootstrap_ci_multinomial if multinomial else bootstrap_ci)(diffs)
    return {'pairs': len(tasks), 'b_only': wins, 'a_only': losses, 'diff_pp': 100 * sum(diffs) / len(tasks),
            'ci_pp': (100 * ci[0], 100 * ci[1]), 'p': mcnemar(wins, losses)}


def holm(pvalues):
    """Holm step-down adjusted p values in the original order."""
    out = [None] * len(pvalues)
    running = 0.0
    for rank, i in enumerate(sorted(range(len(pvalues)), key=lambda j: (pvalues[j], j))):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        out[i] = running
    return out
