# LOGICWorld — 3-Minute Talk Script

**Total: ~450 words ≈ 3 minutes at a natural pace (145–150 wpm).**
Time cues match the `⏱` markers on the slides. *(italics)* = delivery notes.

---

## Slide 1 — Title (0:00–0:12)

Hello everyone. I'm Gangao Liu. Today I'd like to share our work-in-progress benchmark, **LOGICWorld**, which automatically generates deep logical tasks to probe interactive reasoning in embodied agents.

## Slide 2 — Motivation (0:12–0:36)

Let me start with a command we've probably all used: *"If there is a Coke in the fridge, bring it to me; otherwise, go to the kitchen and turn off the light."*

For a robot, this is genuinely hard. It can't follow a pre-computed path — it may need to open the fridge, **observe**, update its belief, and **branch** its plan. Many existing benchmarks, like ALFRED, tend to focus on static, sequential goal lists — great for testing grounding, but logic itself is somewhat under-tested. That's the gap we tried to address.

## Slide 3 — Cognitive Framework (0:36–1:00)

LOGICWorld organizes 1,182 tasks into three levels of cognitive demand. **Level one**, Spatial Execution — long-horizon navigation, the baseline. **Level two**, State Tracking — priority, conditional, and multi-goal tasks that demand working memory. And **Level three**, Compositional Reasoning — instructions driven by expressions like *A and (B or C)*, with up to six branches and over a hundred predicates. Everything runs on a thousand diverse PROCTHOR scenes.

## Slide 4 — Task Generation (1:00–1:22)

To generate such tasks at scale, our pipeline composes atomic tasks with AND and OR, expands them with logical conditions, binds every condition to a verification function, and adds a fallback branch to help guarantee feasibility. Each task therefore comes with a natural-language instruction **and** a machine-checkable verification function — generated together.

## Slide 5 — Scenario Stories (1:22–1:44)

One thing we added recently: we found raw conditional instructions read a bit like if-else lists — not quite how people talk. So we built a rewriting stage where an LLM turns each task into a second-person scenario story, with characters and motivation, while conditions are woven into the narrative. Strict fidelity rules forbid adding or dropping any condition, action, object, or ordering — and a rule-based validator double-checks names, quantities, and phrasing, retrying when needed. All 1,182 stories are done, each keeping the original verification function unchanged.

## Slide 6 — Formulation (1:44–2:04)

Formally, the whole task is one disjunction: at least one branch must satisfy both its logical conditions *f* and its task validator *g*. The environment is **partially observable** — "apple in fridge" is never broadcast; the agent must physically explore to resolve it. Our agent uses a reasoning loop that emits action chunks — several primitives per turn — halting on failure.

## Slide 7 — Main Results (2:04–2:32)

So what did we find? The best model we evaluated, Claude Haiku, goes from **100 percent** on spatial tasks to **86** on state tracking, and **75.8** on compositional reasoning. Qwen3-4B drops to 15 percent on Logic tasks. Past fifty predicates, only frontier models stayed above 60 percent. To us, this suggests the bottleneck is logical state tracking rather than motor control — though we're cautious about over-interpreting single-model results.

## Slide 8 — Ablations (2:32–2:46)

Two ablations worth mentioning. Action chunking cut token cost by about **14 percent** with only a small success drop. And removing CoT cost Qwen3-Max over **32 points**, while GPT-5-Mini barely moved — which *hints* at implicit reasoning in some frontier models, though we'd want more evidence.

## Slide 9 — Conclusion (2:46–3:00)

To summarize: LOGICWorld is our attempt to combine the rigor of classical planning with open-world LLM agents, and to pinpoint where they struggle — deep, non-linear logical branching. It's fully open-sourced, and we'd genuinely welcome feedback. Thank you!

---

## Q&A Backup (not timed)

- **Why not just PDDL?** PDDL requires complete symbolic state; our tasks are partially observable and require exploration to resolve predicates. We combine PDDL-style rigor with open-world semantics — it's a trade-off, not a replacement.
- **How faithful are the generated stories, really?** The validator is rule-based (names, quantities, ordering, phrasing), and each record keeps the original task alongside the story for manual comparison — but we can't guarantee full semantic equivalence and welcome scrutiny.
- **Isn't 75% for Claude already good?** These are still deterministic, abstracted environments with text observations. Adding perception noise and real manipulation would likely make it harder.
- **How is task validity guaranteed?** The fallback branch in the OR-aggregation helps ensure a satisfiable path exists; validation functions are synthesized jointly with instructions.
