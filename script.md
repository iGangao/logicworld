# LOGICWorld — 3-Minute Talk Script

## Slide 1 — Title

Hello everyone, I’m Gangao Liu. Today I’ll introduce **LOGICWorld**, a benchmark for testing logical reasoning in embodied agents.

## Slide 2 — Motivation

Consider: *"If there is a Coke in the fridge, bring it to me; otherwise, turn off the kitchen light."*

A robot must explore the environment, track states, and choose the correct branch. Existing benchmarks such as ALFRED mainly test static goals, so this logical aspect is under-evaluated.

## Slide 3 — Cognitive Framework

LOGICWorld contains 1,182 tasks across three levels:
Spatial Execution, State Tracking, and Compositional Reasoning.
The tasks are generated in 1,000 PROCTHOR scenes, with instructions involving conditional branches, multiple goals, and over a hundred predicates.


## Slide 4-5 — Overview /Task Generation

Each task combines atomic subtasks using AND and OR, links every condition to a verifier, and includes a fallback branch to ensure feasibility. An LLM then rewrites the formal task into a natural second-person instruction, while rule-based validation guarantees that the logic remains unchanged.

## Slide 8-9 — Main Results

Our results show that Claude Haiku achieves 100% on spatial tasks, but only 75.8% on compositional reasoning. Qwen3-4B falls to around 15%. As logical complexity increases, only frontier models remain above 60%.

Performance drops particularly sharply from simple conditions to priority and logic tasks, showing that the main bottleneck is logical state tracking—not navigation or grounding.

## Slide 10 — Ablations

Finally, action chunking reduces token cost by 14%, while removing chain-of-thought hurts smaller models much more than frontier models.

## Slide 11 — Conclusion

In short, LOGICWorld combines classical planning with open-world embodied agents and reveals their weakness in deep logical branching. Thank you!
