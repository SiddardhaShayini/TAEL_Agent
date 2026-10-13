# TAEL Datasets Generation Suite (`TAEL_Datasets/`)

This directory contains the **11 reproducible dataset builder scripts** used to construct the **29,900-sample (~365 MB)** multi-phase training curriculum for **TAEL V2 (`Granite-Final-Agent-GGUF`)**.

---

## Dataset Splits & Builder Scripts

| Builder Script | Generated Output (`dataset/`) | Samples | Size | Training Phase | Primary Upstream Sources |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `build_programming.py` | `01_programming.jsonl` | 15,000 | 23.8 MB | Phase 1 | `bigcode/self-oss-instruct-sc2-exec-filter-50k`, `m-a-p/CodeFeedback-Filtered-Instruction` |
| `build_debugging.py` | `02_debugging.jsonl` | 2,400 | 6.9 MB | Phase 2 | `nebius/SWE-agent-trajectories`, `m-a-p/CodeFeedback-Filtered-Instruction` |
| `build_refactoring.py` | `03_refactoring.jsonl` | 2,000 | 5.7 MB | Phase 2 | `m-a-p/CodeFeedback-Filtered-Instruction` |
| `build_repository.py` | `04_repository.jsonl` | 500 | 0.4 MB | Phase 3 | `tianyang/repobench_python_v1.1`, `nebius/SWE-agent-trajectories` |
| `build_planning.py` | `05_planning.jsonl` | 2,000 | 198.8 MB | Phase 3 | `SWE-bench/SWE-smith-trajectories` |
| `build_architecture.py` | `06_architecture.jsonl` | 1,000 | 3.6 MB | Phase 1 | `m-a-p/CodeFeedback-Filtered-Instruction` |
| `build_testing.py` | `07_testing.jsonl` | 2,000 | 2.8 MB | Phase 1 | `bigcode/self-oss-instruct-sc2-exec-filter-50k` |
| `build_terminal.py` | `08_terminal.jsonl` | 1,000 | 25.1 MB | Phase 3 | `open-thoughts/AgentTrove` |
| `build_git.py` | `09_git.jsonl` | 1,000 | 45.4 MB | Phase 3 | `open-thoughts/AgentTrove` |
| `build_tooluse.py` | `10_tooluse.jsonl` | 2,000 | 50.4 MB | Phase 3 | `open-thoughts/AgentTrove` |
| `build_swe_agent.py` | `11_swe_agent.jsonl` | 1,000 | 1.0 MB | Phase 3 | `nebius/SWE-agent-trajectories` |

---

## Reproducing the Datasets

```powershell
pip install datasets tqdm
cd TAEL_Datasets
python build_programming.py
python build_debugging.py
python build_refactoring.py
python build_repository.py
python build_planning.py
python build_architecture.py
python build_testing.py
python build_terminal.py
python build_git.py
python build_tooluse.py
python build_swe_agent.py
```
