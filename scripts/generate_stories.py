"""Batch-generate scenario stories for tasks in data/logicworld/test.jsonl.

Usage:
    python scripts/generate_stories.py --batch 10 [--start-index N] [--max-retries 2]

Generates the next N unprocessed items, appends results to
data/logicworld/test_stories.jsonl (resumable), and prints a per-item
validation summary for manual review.
"""

import argparse
import json
import os
import re
import sys

from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "data/logicworld/test.jsonl")
OUTPUT_PATH = os.path.join(ROOT, "data/logicworld/test_stories.jsonl")

MODEL = "glm-5.2"

PROMPT_TEMPLATE = """You are rewriting a robot task description as a short scenario story for an embodied-AI benchmark.

Original task:
{task}

The environment is a house. Objects referenced: {objects}.

Rewrite rules — violating any of these makes the output invalid:

SEMANTIC FIDELITY (most important):
1. Do NOT present the task as a branching structure. No "if A then X, else Y" decision lists. Conditions must be woven into natural narrative (e.g. "keep an eye out for X while you search — should you spot it, head to Y instead").
2. Every conditional branch of the task (including fallbacks) must be preserved in the story. Never drop a fallback branch.
2b. Keep each condition tightly bound to its actions: never present an action detached from its condition, and never state a condition without immediately saying what to do in that case. When one condition governs several action options, present all options together under that same condition. Never SPLIT a group of actions that shares one condition into separately-conditioned parts — the group stays whole under its exact condition, even if that condition looks contradictory or redundant (e.g. a condition requiring X and not X at once must be preserved verbatim, not restructured).
2c. NEVER use "whether or not ...", "regardless of whether ...", or similar phrasing to detach an action from its condition. If the task makes an action depend on a condition, the story must keep that dependency. "Whether or not" is only acceptable when the task itself applies the same action under both outcomes of a condition (e.g. "if X, do Y; if not X, do Y"). Also never weaken an action: "find and go to X" must stay a search plus a visit, not just "locate X".
2d. NEVER claim that a condition by itself completes or satisfies the task — phrases like "that alone fulfills the task", "this condition alone satisfies the requirement", "in which case the task requires no further action" are FORBIDDEN. If a condition is one disjunct of a larger condition that governs actions, the actions stay attached to the WHOLE condition ("should A be true, or should B hold, then do X" — never split B off into a standalone no-action clause).
3. Never state a condition as settled fact. Existence, quantities, container relations, and whether something is seen/visited are UNRESOLVED at story time. Write "should there be no plate..." not "there is no plate, so...".
4. Do not add or remove target objects. Only the objects listed above may appear as task targets. No new targets, none missing.
5. Do not add extra actions beyond what the task requires. The motivation must not imply extra actions either — no "needs to be lit", "wants to reposition it", "so she can cook with it" for a task that is only about visiting/accessing items.
5b. Do NOT invent fallback behavior. If the task says nothing about what to do when a condition is not met, the story must not either — no "stay where you are", "remain at X", "continue searching", "return to X". State the conditional exactly as the task does.

PHRASING:
6. Object names must appear verbatim (exact spelling and case, e.g. "DishSponge_1", "peppershaker"). Do not paraphrase object names.
7. Quantities must be exact: "more than 4", "exactly 2". No vague words like "several".
8. Ordering must be explicit for ordered tasks: "first ... then ... after that ...". Order must match exactly. Conversely, do NOT impose an order on tasks that do not specify one — words like "first", "then", "after that", "next" must NEVER connect the actions of a single task unless the task itself states an order; just join them neutrally with "and".
9. Container relations: keep "on/in" relations explicit ("if there is an alarmclock on the dresser").
10. Negations must be explicit ("does not exist"), not softened ("might not be there").
10b. When one negation contains another (e.g. NOT(A AND NOT(B AND NOT(C)))), make the nesting unmistakable with explicit bracketing: "it is not the case that both A and ...", "either ... or ...", "and that it is not the case that ...", "or that it is not the case that ...". NEVER join two "it is not the case that ..." clauses with a bare "and"/"or" (e.g. "...it is not the case that A and it is not the case that B...") — a bare conjunction reads as two separate negations (not-A AND not-B) and changes the meaning.
11. Distinguish seeing during search ("spotted while searching") from actually visiting ("stopped by").

STORY & ENDING:
12. You may invent characters, motivation, background. The story explains WHY the task matters, then naturally turns it into instructions. The setup must be concrete and reference the actual goal of the task — no generic filler like "she could use an extra hand" without saying what for. The actor is always "you" (second person); the character only provides motivation, never performs the search/actions themselves.
13. If the story names a character who needs the task done, end with a sentence like "Now you come and help <character> complete the task." — this closing sentence must come AFTER all task instructions, never before or in the middle. Do not enumerate the task's objects as a scenery/inventory list ("The house holds a Tomato_1, a Lettuce_1, ...") — objects may only appear inside their conditions and instructions.
14. The final sentence(s) must be imperative task instructions addressed to "you", capturing the full task.
15. Never mention the verify expression, task type, house id, or any dataset metadata.
16. Write in English. Keep it to one paragraph (a bit longer is fine for tasks with many conditions).

Output ONLY the story text, nothing else."""


def load_data():
    items = []
    with open(INPUT_PATH) as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            d["_index"] = i
            items.append(d)
    return items


def load_done_indices():
    done = set()
    if not os.path.exists(OUTPUT_PATH):
        return done
    with open(OUTPUT_PATH) as f:
        for line in f:
            try:
                done.add(json.loads(line)["_index"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def extract_objects(verify):
    return sorted(set(re.findall(r"'([^']+)'", verify)))


BRANCH_PATTERNS = [
    r"\bif\s+.*\s+else\b",
    r"\boption\s+[AB1-2]\b",
    r"\bcase\s+\d+\s*:",
    r"^\s*[-*\d]+[.)]\s",  # numbered/bulleted list
    r"\botherwise\s*:",
]


def verify_target_conflict(verify):
    """Heuristic: if every top-level OR-branch of verify requires located/hold on
    the same target, verify demands that target unconditionally — which
    contradicts a conditional task reading. Returns the conflicting target."""
    import ast

    try:
        tree = ast.parse(verify.strip(), mode="eval").body
    except SyntaxError:
        return None
    branches = tree.values if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.Or) else [tree]
    if len(branches) < 2:
        return None
    targets_per_branch = []
    for b in branches:
        targets = set()
        for node in ast.walk(b):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("located", "hold") and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant):
                        targets.add(arg.value)
        if not targets:
            return None
        targets_per_branch.append(targets)
    common = set.intersection(*targets_per_branch)
    return sorted(common) if common else None


def impossible_branch(verify):
    """count_receptacle_items(...) < 0 is always false — dataset bug making that
    verify branch unsatisfiable."""
    return bool(re.search(r"<\s*0\b", verify))


def extract_required_numbers(verify):
    """Numbers from count comparisons (==N, >N, >=N, <N, <=N) and category-place counts."""
    nums = set()
    for m in re.finditer(r"[<>=!]=?\s*(\d+)", verify):
        n = int(m.group(1))
        if n > 0:
            nums.add(str(n))
    # verify_category_place_task('x', [...], [1, 1]) — the count list args
    for m in re.finditer(r"verify_category_place_task\([^)]*\[([^\]]*)\]\)", verify):
        for n in re.findall(r"\d+", m.group(1)):
            if n != "0":
                nums.add(n)
    return nums


def extract_visit_order(verify):
    """For order_* tasks: items sorted by ascending priority (verify arg order)."""
    m = re.search(r"verify_order_\w+_task\((.*)\)\s*$", verify.strip())
    if not m:
        return None
    import ast
    lists = re.findall(r"\[[^\]]*\]", m.group(1))
    if len(lists) < 2:
        return None
    items = ast.literal_eval(lists[0])
    prios = ast.literal_eval(lists[-1])
    return [it for _, it in sorted(zip(prios, items), key=lambda t: t[0])]


def order_problem(item, story):
    order = extract_visit_order(item["verify"])
    if not order:
        return None
    pos = 0
    for it in order:
        idx = story.find(it, pos)
        if idx == -1:
            return f"items not in priority order: {order}"
        pos = idx + 1
    return None


def extract_category_counts(verify):
    """category_place: (receptacle, [(item, required_count), ...])."""
    m = re.search(r"verify_category_place_task\('([^']+)', (\[[^\]]*\]), (\[[^\]]*\])\)", verify)
    if not m:
        return None
    import ast
    return m.group(1), list(zip(ast.literal_eval(m.group(2)), ast.literal_eval(m.group(3))))


NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def extract_num_place(verify):
    """num_place: [(receptacle, item, required_count), ...] from == comparisons."""
    placements = []
    for m in re.finditer(r"count_receptacle_items\('([^']+)',\s*'([^']+)'\)\s*==\s*(\d+)", verify):
        placements.append((m.group(1), m.group(2), int(m.group(3))))
    return placements


def has_number(story, n):
    return bool(re.search(rf"\b{n}\b", story) or (
        n in NUM_WORDS and re.search(rf"\b{NUM_WORDS[n]}\b", story, re.IGNORECASE)
    ))


def validate_num_place(item, story):
    """verify pins exact counts on specific receptacle instances; the story must
    name those instances (even where the task text says 'any one X') and the
    exact counts."""
    problems = []
    for receptacle, name, c in extract_num_place(item["verify"]):
        if name not in story:
            problems.append(f"missing object name: {name}")
        if receptacle not in story:
            problems.append(f"missing receptacle name: {receptacle}")
        if not has_number(story, c):
            problems.append(f"missing quantity: {c} for {name} on {receptacle}")
    return problems


def validate_category_place(item, story):
    """verify requires counts == item_counts exactly, so nonzero counts must be
    stated explicitly and zero-count items must not be mentioned at all."""
    problems = []
    parsed = extract_category_counts(item["verify"])
    if not parsed:
        return problems
    _, pairs = parsed
    for name, c in pairs:
        if c > 0:
            if name not in story:
                problems.append(f"missing object name: {name}")
            has_num = re.search(rf"\b{c}\b", story) or (
                c in NUM_WORDS and re.search(rf"\b{NUM_WORDS[c]}\b", story, re.IGNORECASE)
            )
            if not has_num:
                problems.append(f"missing quantity: {c} for {name}")
        elif re.search(rf"\b{re.escape(name)}\b", story, re.IGNORECASE):
            problems.append(f"mentions zero-count object: {name}")
    return problems


def validate_story(item, story):
    problems = []
    op = order_problem(item, story)
    if op:
        problems.append(op)
    if item["task_type"] == "category_place":
        problems += validate_category_place(item, story)
    elif item["task_type"] == "num_place":
        problems += validate_num_place(item, story)
    else:
        for obj in extract_objects(item["verify"]):
            if obj not in story:
                problems.append(f"missing object name: {obj}")
        for n in extract_required_numbers(item["verify"]):
            if n != "1" and not re.search(rf"\b{re.escape(n)}\b", story):
                problems.append(f"missing quantity: {n}")
    for pat in BRANCH_PATTERNS:
        m = re.search(pat, story, re.IGNORECASE | re.MULTILINE)
        if m:
            problems.append(f"branch-like phrasing: ...{m.group(0)[:40]!r}...")
    for meta in (item["house"], "task_type", "verify", "self.", "<think"):
        if meta in story:
            problems.append(f"metadata leak: {meta}")
    return problems


def category_hint(item):
    if item["task_type"] != "category_place":
        return "", []
    parsed = extract_category_counts(item["verify"])
    if not parsed:
        return "", []
    receptacle, pairs = parsed
    targets = [name for name, c in pairs if c > 0]
    reqs = ", ".join(f"exactly {c} {name}" for name, c in pairs if c > 0)
    hint = (
        f"\n\nPlacement contract: when you are done, the {receptacle} must hold {reqs} "
        "(no more, no fewer). The story must state these exact numbers. "
        "Keep \"on/in the <receptacle>\" explicit."
    )
    zero = [name for name, c in pairs if c == 0]
    if zero:
        hint += f" Do NOT mention {' or '.join(zero)} anywhere in the story."
    return hint, targets


def num_place_hint(item):
    if item["task_type"] != "num_place":
        return "", []
    placements = extract_num_place(item["verify"])
    if not placements:
        return "", []
    reqs = "; ".join(f"exactly {c} {name} on/in the {receptacle}" for receptacle, name, c in placements)
    hint = (
        f"\n\nPlacement contract: when you are done, the following must hold exactly — {reqs}. "
        "The receptacle names above are specific instances and must appear verbatim in the story. "
        "Where the task text says 'any one <receptacle>', the story must instead name the specific "
        "instance from this contract. State the exact numbers."
    )
    targets = []
    for receptacle, name, _ in placements:
        targets += [name, receptacle]
    return hint, targets


def generate(client, item, feedback=None):
    hint, targets = category_hint(item)
    if not hint:
        hint, targets = num_place_hint(item)
    objects = targets or extract_objects(item["verify"])
    prompt = PROMPT_TEMPLATE.format(
        task=item["task"],
        objects=", ".join(objects),
    ) + hint
    if feedback:
        prompt += (
            f"\n\nYour previous attempt had these problems: {feedback}\n"
            "Rewrite the story fixing all of them. Output ONLY the corrected story."
        )
    content = ""
    for max_tokens in (16384, 65536):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        content = (resp.choices[0].message.content or "").strip()
        content = re.sub(r"</?think>", "", content).strip()
        if content:
            return content
        # model burned the whole budget on reasoning (finish_reason=length); retry larger
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--start-index", type=int, default=None, help="force start index (ignore progress)")
    args = ap.parse_args()

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", ""),
    )

    data = load_data()
    done = load_done_indices() if args.start_index is None else set()
    todo = [d for d in data if d["_index"] not in done]
    todo.sort(key=lambda d: d["_index"])
    batch = todo[: args.batch]
    if not batch:
        print("All done.")
        return

    print(f"Generating {len(batch)} stories (indices {batch[0]['_index']}..{batch[-1]['_index']}), "
          f"{len(todo) - len(batch)} remaining after this batch.\n")

    results = []
    for item in batch:
        story = None
        problems = ["generation failed"]
        feedback = None
        for attempt in range(3):
            try:
                story = generate(client, item, feedback)
            except Exception as e:
                problems = [f"API error: {e}"]
                continue
            if story is None:
                problems = ["model returned empty content"]
                continue
            problems = validate_story(item, story)
            if not problems:
                break
            feedback = problems
            print(f"  [idx {item['_index']}] retry {attempt + 1}: {problems}")
        conflict = verify_target_conflict(item["verify"])
        record = {
            "_index": item["_index"],
            "house": item["house"],
            "task": story if story else item["task"],
            "task_original": item["task"],
            "verify": item["verify"],
            "task_type": item["task_type"],
            "type_num": item.get("type_num"),
            "meta": {
                "retries": attempt,
                "problems": problems,
                "passed": not problems,
                "verify_target_conflict": conflict,
                "verify_impossible_branch": impossible_branch(item["verify"]),
            },
        }
        results.append(record)

    with open(OUTPUT_PATH, "a") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    passed = sum(1 for r in results if r["meta"]["passed"])
    print(f"\nBatch done: {passed}/{len(results)} passed rule checks.")
    for r in results:
        status = "OK " if r["meta"]["passed"] else "FAIL"
        print(f"[{status}] idx={r['_index']} type={r['task_type']}")
        if not r["meta"]["passed"]:
            print(f"       problems: {r['meta']['problems']}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
