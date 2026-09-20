# LOGICWorld — 3-Minute Talk Script

## Slide 1 — Title (0:00–0:10)

Hello everyone, I'm Gangao Liu. Today I'll present our benchmark, **LOGICWorld** — it automatically generates deep logical tasks for embodied agents.

## Slide 2 — Motivation (0:10–0:35)

Consider: *"If there is a Coke in the fridge, bring it to me; otherwise, turn off the kitchen light."*

For a robot, this is hard — it must **observe** and **branch** its plan. Existing benchmarks like ALFRED mostly test static goal lists; the logic itself is under-tested. That's our gap.

## Slide 3 — Cognitive Framework (0:35–1:00)

LOGICWorld has 1,182 tasks in three levels: **Spatial Execution** — long-horizon navigation; **State Tracking** — conditional and multi-goal tasks needing working memory; and **Compositional Reasoning** — instructions like *A and (B or C)*, with up to six branches and over a hundred predicates. All on a thousand PROCTHOR scenes.

## Slide 4 — Overview (1:00–1:12)

*(point at the figure)* This figure contrasts static tasks with ours — logic governs execution, and each task pairs an instruction with a verification function.

## Slide 5 — Task Generation (1:12–1:32)

Our pipeline composes atomic tasks with AND and OR, binds every condition to a verification function, and adds a fallback branch to guarantee feasibility.

## Slide 6 — Scenario Stories (1:32–1:56)

Raw conditional instructions read like if-else lists. So an LLM rewriting stage turns each task into a second-person story. Fidelity rules forbid changing any condition, and a rule-based validator double-checks every story. All 1,182 are done, with verifiers unchanged.

## Slide 7 — Formulation (1:56–2:14)

Formally, each task is one disjunction — at least one branch must satisfy its conditions and validator. The environment is **partially observable**: the agent must physically explore. Our agent emits action chunks each turn, halting on failure.

## Slide 8 — Main Results (2:14–2:38)

Claude Haiku scores **100** on spatial tasks, **86** on state tracking, **75.8** on compositional reasoning. Qwen3-4B drops to 15 percent. And as predicate count grows, only frontier models stay above 60. So the bottleneck is logical state tracking, not navigation or grounding.

## Slide 9 — Per-Type Results (2:38–2:50)

*(gesture at the heatmap)* By subtype, success drops steeply from Condition to Priority and Logic tasks — smaller models stall below 45 percent even with more steps.

## Slide 10 — Ablations (2:50–2:58)

Ablations: action chunking cut token cost by **14 percent**. Removing CoT cost Qwen3-Max **32 points**, while GPT-5-Mini barely moved.

## Slide 11 — Conclusion (2:58–3:10)

In short: LOGICWorld combines classical planning rigor with open-world LLM agents, and pinpoints where they struggle — deep logical branching. It's fully open-sourced — thank you!
