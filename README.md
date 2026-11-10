# Beyond Localization

Code and data for the paper *Beyond Localization: How Does Telling an LLM Where to Edit Help Repository-Level Program Repair?*

Repair systems localize first and then ask an LLM to write the patch.
This study measures whether naming the functions to modify still helps once their code is already in the prompt.
Paired prompts keep the candidate code and its order fixed and differ only in whether they name the developer-modified functions.
The repository contains every per-response outcome behind the paper, the scripts that recompute its tables and figures, and the raw prompts, responses, agent trajectories, and test reports.

## Quick start

Python 3.10 or newer is enough to recompute every table.

```bash
pip install -r requirements.txt
python analysis/reproduce.py              # all tables
python analysis/reproduce.py identity-effects agent   # selected tables
python analysis/figures.py                # Figures 2 and 3 into figures/
```

The raw archives are stored with Git LFS.
Clone with Git LFS installed, or run `git lfs pull` after cloning, to fetch them.

## Experiments

| Experiment | Setting | Size |
|---|---|---|
| Candidate experiment | 181 screened SWE-bench Lite tasks and 274 screened SWE-bench Verified tasks, 0, 10, or 20 other candidate functions, known and unknown prompts | 3,021 response slots from DeepSeek Flash, Qwen3-Coder-30B-A3B-Instruct, and GLM-4.5-Air |
| Native localizer candidates | Agentless's function-level localization output on the 181 Lite tasks, conditions A, B, and C | 543 task-condition cells with Qwen3-Coder-30B-A3B-Instruct |
| Agent experiment | mini-SWE-agent 2.4.6 on the 413 distinct screened tasks, marked and unmarked task text | 1,652 runs with Qwen3-Coder-30B-A3B-Instruct and GLM-4.5-Air |
| System experiments | Agentless, KGCompass, and ExpeRepair on the 300 SWE-bench Lite tasks with DeepSeek-V3, final predictions and 10-sample Oracle pools with added evidence | 300 tasks per condition |
| Failure labels | Failure causes of 257 failed candidate responses, labeled by GPT-6.1 through the Codex CLI with an 8-cause codebook | 257 labels and 100 control responses |

## Paper tables and figures

| Paper | `reproduce.py` argument | Data |
|---|---|---|
| Table 2 | `candidate-outcomes` | `data/candidate/responses.csv` |
| Table 3 | `count-contrasts` | `data/candidate/responses.csv` |
| Table 4 and the Holm families | `identity-effects` | `data/candidate/responses.csv` |
| Table 5 | `stage-transitions` | `data/candidate/responses.csv` |
| Table 6 and Figure 2 | `reference-success`, `figures.py` | `data/candidate/responses.csv` |
| Table 7 | `discordant-sets` | `data/candidate/responses.csv` |
| Table 8 | `candidate-composition` | `data/candidate/responses.csv`, `data/candidate/composition.csv` |
| Table 9 | `issue-strata` | `data/candidate/responses.csv`, `data/tasks.csv` |
| Tables 10 and 11 | `native-candidates` | `data/native/responses.csv` |
| Tables 12 and 13 | `agent` | `data/agent/runs.csv` |
| Tables 14 and 15 | `oracle-main` | `data/system/final_predictions.csv` |
| Tables 16 and 17 | `samples` | `data/system/sample_frequencies/`, `data/system/final_predictions.csv` |
| Tables 18 to 20 | `evidence` | `data/system/evidence_controls.csv`, `data/system/sample_frequencies/` |
| Table 21 | `output-tail` | `data/candidate/responses.csv` |
| Table 22 | `failure-causes` | `data/failure_labels.csv` |
| Screened Lite 181 rows of Tables 14, 15, 17, and 19, and the 181-task counts of RQ4 | `screened_subset.py` | `data/system/`, `data/tasks.csv` |
| Figure 3 | `figures.py` | `data/system/final_predictions.csv`, `data/system/sample_frequencies/` |

The script also prints analyses that the paper does not tabulate: repetition-loop counts per condition with `loop-counts`, the shared-prompt comparison with `shared-prompt`, and the all-sample success counts within `evidence`.

Paired comparisons use exact two-sided McNemar tests and percentile 95% task-bootstrap intervals with 10,000 replicates and seed 20261024, as implemented in `analysis/stats.py`.

## Data

`data/tasks.csv` lists every task with its membership in the 300-task Lite split, the 181 screened Lite tasks, and the 274 screened Verified tasks, and whether the issue names all, some, or none of the developer-modified functions.

`data/candidate/responses.csv` has a row per response slot of the candidate experiment.

| Column | Meaning |
|---|---|
| `llm`, `cohort` | `deepseek`, `qwen`, or `glm`; `C1` for the 181 Lite tasks and `C3` for the other 232 Verified tasks |
| `m`, `condition` | Number of other candidate functions; `known` or `unknown` |
| `finish_reason`, `output_tokens` | Completion reason and, for DeepSeek, output tokens |
| `stage` | `tested`, `no_patch`, `processing_failure`, `test_timeout`, or `no_response` |
| `resolved` | Official test outcome, empty when unscored |
| `touch_g`, `touch_all_g`, `outside_g` | Whether the final patch edits at least 1, all, or none outside the developer-modified functions |
| `distractor_touch`, `nonempty_patch` | Whether the final patch edits another presented candidate, and whether it is nonempty |
| `g_edited`, `files` | Edited developer-modified functions and edited files |

The 42 tasks shared by the 2 screened sets reuse their Lite responses in the Verified views.

`data/candidate/composition.csv` records how many presented candidates share a file with the developer-modified functions.
`data/native/responses.csv` and `data/agent/runs.csv` hold the outcomes of the native-candidate and agent experiments.
`data/system/` holds the final predictions and 10-sample success counts of the 3 repair systems, the shared-prompt summary, and the added-evidence comparisons with their filler and wrong-evidence controls.
`data/failure_labels.csv` holds the failure cause and the labeler's explanation for each labeled response.

## Raw archives

| Archive | Contents |
|---|---|
| `archives/candidate_sets.tar.gz` | Candidate sets of every task and the screening labels |
| `archives/candidate_responses.tar.gz` | Request, raw API response, and output text of every candidate response |
| `archives/candidate_evaluations.tar.gz` | Evaluated patch, official report, and test output of every candidate response |
| `archives/native_candidates.tar.gz` | Agentless's localization output, the native-candidate prompts and responses, and the evaluated patches |
| `archives/agent_runs.tar.gz` | Agent trajectories and the official reports of the submitted and working-tree diffs |
| `archives/failure_labels.tar.gz` | Codebook, labeling prompts, and the labeler's raw outputs |

Response headers and runtime state files are not included.
In agent trajectories, the cluster account and project names are replaced by `user` and `project`.

## Settings and accounting

These details complement the paper.

- DeepSeek Flash is the vendor service `deepseek-flash`, documented as DeepSeek-V4.1-Flash-1017 and accessed in October 2026 with temperature 0, top-p 1, thinking disabled, and a 393,216-token output limit.
- Qwen3-Coder-30B-A3B-Instruct runs at revision `b2cff646` in BF16 through vLLM. GLM-4.5-Air runs in BF16 through vLLM with 4-way tensor parallelism and its thinking mode disabled. Both use temperature 0, top-p 1, top-k -1, a repetition penalty of 1.0, an 8,192-token output limit, and seed 20261025.
- The candidate experiment has 3,021 response slots: 905 Lite and 464 Verified slots for DeepSeek, and 362 Lite and 464 Verified slots each for Qwen and GLM. The Verified slots cover the 232 Verified tasks outside the screened Lite set. 6 DeepSeek requests returned no response, and 3 test runs of Qwen and GLM reached the test limit without a report. These 9 slots have an empty `resolved` value and stage `no_response` or `test_timeout`.
- A function is identified by its repository-relative path, qualified name, and pre-patch start line. Candidate sets exclude duplicate, overlapping, and containing source ranges. Patches whose mapping to functions is ambiguous at a boundary have empty edit columns.
- The native-candidate experiment has 543 task-condition cells and 417 generated responses, because condition B reuses condition A's response on the 126 tasks whose native candidates already cover the developer-modified functions. A single condition A test run reached the test limit and counts as unresolved.
- Official evaluation uses SWE-bench harness commit `726c5461e2ef52d83cf1ea2107870a8bb3328d57` with 1 CPU, 6 GiB of memory, a 600-second test limit, and a 750-second process limit.
- The 3 Verified identity views cover all 274 tasks, the 232 tasks outside the screened Lite set, and the 222 tasks outside the 300-task Lite split. Lite has 65, 6, and 110 tasks whose issue names all, some, or none of the developer-modified functions, and Verified has 119, 12, and 143.
- The failure codebook was fixed after a 20-response pilot. On 100 control responses, the labeler agrees with the automated facts on 100, 92, and 98 answers about whether the patch edits the developer-modified functions, whether its target tests pass, and whether the response names these functions before its first edit.
- Wrong-evidence controls longer than their informative prompt are truncated at the tail to the matched token budget.

## Repair systems

The modified Agentless, KGCompass, and ExpeRepair pipelines and their original runs for the system experiments are archived on Zenodo at <https://doi.org/10.5281/zenodo.19232375>.
This repository contains the per-task outcomes of those runs that the paper reports.

## License

The code and data in this repository are released under the MIT License.
The candidate code and issue texts come from the SWE-bench benchmarks and their source repositories, which keep their own licenses.
