# LOGICWorld

**LOGICWorld: Automated Deep Logic Generation for Interactive Reasoning in Embodied Agents**

**English** | [中文](README_ZH.md)

<p align="center">
  <img src="docs/assets/overview.png" alt="LOGICWorld overview" width="100%"/>
</p>

<p align="center">
  <em>From linear household goals to deep propositional logic with dynamic branching and automated goal verification.</em>
</p>

LOGICWorld is a cognitive evaluation framework and Gymnasium environment for testing whether embodied agents can track logical state machines under **partial observability**. Unlike benchmarks that mainly stress sequential manipulation, LOGICWorld auto-generates conditional instructions such as:

> *If there is a Coke in the fridge, bring it to me; otherwise, go to the kitchen and turn off the light.*

Agents must explore, update beliefs from feedback, evaluate propositional conditions, and replan non-linearly.

<!-- **Paper:** [papers/LOGICWorld_IROS2026.pdf](papers/LOGICWorld_IROS2026.pdf) · **Source:** [papers/LOGICWorld_IROS2026.tex](papers/LOGICWorld_IROS2026.tex) -->

---

## Highlights

- **Cognitive capability ladder** — Spatial Execution → State Tracking → Compositional Reasoning
- **Automated deep-logic generation** — natural-language tasks paired with Boolean verification functions
- **PROCTHOR-scale scenes** — 1,000 test / 10,000 train procedural households, 95 object categories
- **High-level action primitives** — focus evaluation on reasoning, not low-level motor control
- **Interactive CLI** — play episodes in the terminal with `logicworld`

<p align="center">
  <img src="docs/assets/task_generator.png" alt="Task generation pipeline" width="85%"/>
</p>

<p align="center">
  <em>Task description &amp; verification synthesis pipeline (atomic tasks → logical conditions → composition → fallback).</em>
</p>

---

## Cognitive Framework

| Capability | What it tests | Examples |
|---|---|---|
| **Spatial Execution** | Long-horizon navigation & skill chaining | Navigate, PickUp, Place, TurnOn/Off |
| **State Tracking** | Working memory, order, basic `if-else` | Priority, Conditional, Multi-Goal |
| **Compositional Reasoning** | Deep propositional branching | Multi-branch expressions with `AND` / `OR` / `NOT` |

The compositional tier synthesizes instructions and a global verifier of the form:

\[
T = \bigvee_{k=1}^{n}\big[f_k(c_{j_1},c_{j_2},\ldots;\mathcal{L}) \land g_k(V(t_a),V(t_b),\ldots;\mathcal{L})\big]
\]

where \(f_k\) composes state predicates (e.g. `Exist`, `Saw`, `Visited`) and \(g_k\) validates atomic subtask completion.

**Benchmark scale (paper):** 1,182 evaluation tasks; Compositional Reasoning alone contains 532 logic tasks with long instructions (~201 tokens) and dense predicate sets.

---

## Installation

```bash
git clone https://github.com/iGangao/logicworld.git
cd logicworld
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional LLM credentials for `ASK` / `ANSWER`:

```bash
cp .env.example .env
# set LOGICWORLD_API_KEY / LOGICWORLD_BASE_URL / LOGICWORLD_MODEL
```

---

## Quickstart

### Interactive CLI

```bash
logicworld --help
logicworld --house 0 --split test --seed 42
logicworld --auto-task pickup
```

```text
logicworld> help
logicworld> rooms
logicworld> NAVIGATE_TO('Kitchen_1')
logicworld> visible
logicworld> PICK_UP('Apple_1')
logicworld> DONE()
logicworld> quit
```

### Python API

```python
from logicworld import LOGICWorldEnv, load_scene

scene = load_scene("house_0", split="test")
env = LOGICWorldEnv(
    house="house_0",
    scene_data=scene,
    task={
        "task": "Search for any one apple and pick it up.",
        "verify": "self.hold('apple')",
        "task_type": "pickup",
    },
)

obs, info = env.reset(seed=42)
obs, reward, terminated, truncated, info = env.step("NAVIGATE_TO('Kitchen_1')")
```

Gymnasium:

```python
import gymnasium as gym
import logicworld  # noqa: F401
from logicworld import load_scene

env = gym.make(
    "LOGICWorld-v0",
    house="house_0",
    scene_data=load_scene("house_0", split="test"),
    task={"task": "demo", "verify": "True"},
)
```

Also see [`examples/quickstart.py`](examples/quickstart.py).

---

## Action Space

High-level skill primitives (text commands):

| Action | Example |
|---|---|
| `NAVIGATE_TO` | `NAVIGATE_TO('Fridge_1')` |
| `OPEN` / `CLOSE` | `OPEN('Fridge_1')` |
| `PICK_UP` / `DROP` | `PICK_UP('Apple_1')` |
| `PUT_IN` / `PUT_ON` | `PUT_ON('Apple_1', 'CounterTop_1')` |
| `TURN_ON` / `TURN_OFF` | `TURN_ON('DeskLamp_1')` |
| `DONE` / `END` | `DONE()` / `END('impossible')` |
| `ASK` / `ANSWER` | `ASK('Where is the apple?')` |

The environment is **partially observable**: agents must open receptacles and inspect feedback to resolve predicates before choosing a branch.

---

## Data & Configuration

| Resource | Path | Notes |
|---|---|---|
| Train scenes | `data/train.jsonl` | 10,000 households (**not in Git**; ~331 MB, exceeds GitHub 100 MB limit) |
| Test scenes | `data/test.jsonl` | 1,000 evaluation households (tracked) |
| Item affordances | `logicworld/configs/items.json` | placeable / openable / toggleable / pickable |
| Paper figures | `papers/images/` | overview, task generator, ablations |

> **Note:** Keep `data/train.jsonl` on your local machine (already gitignored). CLI / tests only require `data/test.jsonl`. See [`data/README.md`](data/README.md).

```bash
export LOGICWORLD_DATA_DIR=/path/to/data
export LOGICWORLD_ITEMS_CONFIG=/path/to/custom_items.json
```

Generate compositional tasks:

```bash
python scripts/generate_tasks.py \
  --split train \
  --min-rooms 3 \
  --max-rooms 6 \
  --limit 20 \
  --output outputs/conditional.jsonl
```

---

## Repository Layout

```text
logicworld/
  cli.py              # Interactive terminal simulator
  env.py              # LOGICWorldEnv (Gymnasium)
  tasks.py            # TaskGenerator
  config.py           # Item / receptacle config loader
  configs/items.json
  paths.py
data/                 # Scene JSONL
examples/             # Minimal demos
scripts/              # Task generation utilities
docs/assets/          # README figures
papers/
  LOGICWorld_IROS2026.tex
  LOGICWorld_IROS2026.pdf
  images/             # Paper figures (PDF)
tests/
```

---

## Development

```bash
ruff check logicworld examples scripts tests
pytest -q
```

---

## Citation

If you use LOGICWorld, please cite:

```bibtex
@inproceedings{liu2026logicworld,
  title     = {LOGICWorld: Automated Deep Logic Generation for Interactive Reasoning in Embodied Agents},
  author    = {Liu, Gangao and Xu, Huixin and Wang, Mengna and Li, Peng},
  booktitle = {IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)},
  year      = {2026}
}
```

**Authors:** Gangao Liu, Huixin Xu, Mengna Wang, and Peng Li  
**Corresponding author:** Peng Li ([lipeng@iscas.ac.cn](mailto:lipeng@iscas.ac.cn))  
<!-- **Affiliations:** Institute of Software, Chinese Academy of Sciences; University of Chinese Academy of Sciences; Nanjing University of Posts and Telecommunications -->

---

## License

Licensed under the [Mulan Permissive Software License, Version 2 (MulanPSL-2.0)](http://license.coscl.org.cn/MulanPSL2).

See [LICENSE](LICENSE) for the full Chinese and English text.

```text
Copyright (c) 2026 Gangao Liu, Huixin Xu, Mengna Wang, and Peng Li
LOGICWorld is licensed under Mulan PSL v2.
```
