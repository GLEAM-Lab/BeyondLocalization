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
| Table 5 | `loop-counts` | `data/candidate/responses.csv` |
| Table 6 | `stage-transitions` | `data/candidate/responses.csv` |
| Table 7 and Figure 2 | `reference-success`, `figures.py` | `data/candidate/responses.csv` |
| Table 8 | `discordant-sets` | `data/candidate/responses.csv` |
| Table 9 | `candidate-composition` | `data/candidate/responses.csv`, `data/candidate/composition.csv` |
| Table 10 | `issue-strata` | `data/candidate/responses.csv`, `data/tasks.csv` |
| Tables 11 and 12 | `native-candidates` | `data/native/responses.csv` |
| Tables 13 and 14 | `agent` | `data/agent/runs.csv` |
| Tables 15 and 16 | `oracle-main` | `data/system/final_predictions.csv` |
| Tables 17 and 18 | `samples` | `data/system/sample_frequencies/`, `data/system/final_predictions.csv` |
| Table 19 | `shared-prompt` | `data/system/shared_prompt.csv` |
| Tables 20 to 23 | `evidence` | `data/system/evidence_controls.csv`, `data/system/sample_frequencies/` |
| Table 24 | `output-tail` | `data/candidate/responses.csv` |
| Table 25 | `failure-causes` | `data/failure_labels.csv` |
| Figure 3 | `figures.py` | `data/system/final_predictions.csv`, `data/system/sample_frequencies/` |

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

## Repair systems

The modified Agentless, KGCompass, and ExpeRepair pipelines and their original runs for the system experiments are archived on Zenodo at <https://doi.org/10.5281/zenodo.19232375>.
This repository contains the per-task outcomes of those runs that the paper reports.

## License

The code and data in this repository are released under the MIT License.
The candidate code and issue texts come from the SWE-bench benchmarks and their source repositories, which keep their own licenses.
