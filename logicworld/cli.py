"""Interactive terminal simulator for LOGICWorld."""

from __future__ import annotations

import argparse
import sys
import textwrap
from typing import Optional, Tuple

from logicworld import LOGICWorldEnv, __version__, load_scene

HELP_TEXT = """
Commands
--------
  Environment actions (examples):
    NAVIGATE_TO('Kitchen_1')
    OPEN('Fridge_1')
    CLOSE('Fridge_1')
    PICK_UP('Apple_1')
    PUT_ON('Apple_1', 'CounterTop_1')
    PUT_IN('Apple_1', 'Fridge_1')
    DROP('Apple_1')
    TURN_ON('DeskLamp_1')
    TURN_OFF('DeskLamp_1')
    DONE()
    END('impossible')

  Meta commands:
    help / h / ?       Show this help
    look / obs         Show current observation
    status             Show room, location, inventory, steps
    rooms              List rooms in the house
    visible            List currently visible objects
    inventory / inv    List held items
    task               Show current task / verify expression
    actions            List available action names
    reset              Reset episode (same house / task)
    newtask [kind]     Sample a new task (visit|pickup|place|toggle_on|toggle_off|random)
    quit / exit / q    Leave the simulator
""".strip()

AUTO_TASK_KINDS = {
    "visit": "create_visited_item_task",
    "pickup": "create_pickup_item_task",
    "place": "create_place_item_task",
    "toggle_on": "create_toggle_on_item_task",
    "toggle_off": "create_toggle_off_item_task",
    "random": "random_task",
}


def _banner() -> str:
    return textwrap.dedent(
        f"""
        LOGICWorld interactive simulator  v{__version__}
        Type an action like NAVIGATE_TO('Kitchen_1'), or 'help'.
        """
    ).strip()


def _print_block(title: str, body: str) -> None:
    print()
    print(f"=== {title} ===")
    print(body.rstrip())
    print()


def _sample_task(env: LOGICWorldEnv, kind: str) -> Tuple[str, str]:
    method_name = AUTO_TASK_KINDS.get(kind)
    if method_name is None:
        raise ValueError(
            f"Unknown task kind '{kind}'. Choose from: {', '.join(sorted(AUTO_TASK_KINDS))}"
        )
    method = getattr(env.task_generator, method_name)
    for _ in range(20):
        task, verify = method() if kind == "random" else method(1)
        if task and verify:
            return task, verify
    return "Explore the house and call DONE() when finished.", "True"


def _apply_task(env: LOGICWorldEnv, task: str, verify: str) -> None:
    env.task = task
    env.verify = verify
    env.goal_achieved = False


def _status_text(env: LOGICWorldEnv) -> str:
    info = env._get_info()
    return textwrap.dedent(
        f"""
        house:      {env.house}
        room:       {info['current_room']}
        location:   {info['current_location']}
        inventory:  {info['inventory'] or '[]'}
        steps:      {info['steps_taken']} / {env.max_steps}
        goal:       {info['goal_achieved']}
        """
    ).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logicworld",
        description="Interactive LOGICWorld household simulator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            examples:
              logicworld
              logicworld --house 3 --split test --seed 42
              logicworld --auto-task pickup
              logicworld --task "Search for any one apple and pick it up." --verify "self.hold('apple')"
            """
        ),
    )
    parser.add_argument("--version", action="version", version=f"logicworld {__version__}")
    parser.add_argument("--house", default="0", help="House id or index (default: 0)")
    parser.add_argument(
        "--split",
        choices=["train", "test"],
        default="test",
        help="Scene split (default: test)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Episode seed (default: 42)")
    parser.add_argument(
        "--task",
        default="",
        help="Task instruction text (optional)",
    )
    parser.add_argument(
        "--verify",
        default="True",
        help="Python verify expression evaluated on DONE (default: True)",
    )
    parser.add_argument(
        "--auto-task",
        choices=sorted(AUTO_TASK_KINDS),
        default="",
        help="Auto-generate a task after reset",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Use verbose natural-language observations after each step",
    )
    return parser


def create_env(args: argparse.Namespace) -> LOGICWorldEnv:
    house_token = str(args.house)
    if house_token.isdigit() or house_token.startswith("house_"):
        house_id = house_token if house_token.startswith("house_") else f"house_{house_token}"
    else:
        # Allow values like train-house_12; strip prefix for scene lookup.
        house_id = house_token.split("-")[-1]
        if not house_id.startswith("house_"):
            house_id = f"house_{house_id}"

    scene = load_scene(house_id, split=args.split)
    env_house = house_id if args.split == "test" else f"train-{house_id}"
    env = LOGICWorldEnv(
        house=env_house,
        scene_data=scene,
        task={
            "task": args.task or "Explore the house and call DONE() when finished.",
            "verify": args.verify,
            "task_type": args.auto_task or "interactive",
        },
        verbose_feedback=args.verbose,
    )
    return env


def run_repl(env: LOGICWorldEnv, seed: int, auto_task: str = "") -> int:
    obs, info = env.reset(seed=seed)
    if auto_task:
        task, verify = _sample_task(env, auto_task)
        _apply_task(env, task, verify)
        obs = env._get_obs_natural()

    print(_banner())
    _print_block("Observation", obs)
    _print_block("Task", env.task)

    while True:
        try:
            raw = input("logicworld> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not raw:
            continue

        lower = raw.lower()
        if lower in {"quit", "exit", "q"}:
            print("Bye.")
            return 0
        if lower in {"help", "h", "?"}:
            print(HELP_TEXT)
            continue
        if lower in {"look", "obs", "observation"}:
            _print_block("Observation", env._get_obs_natural())
            continue
        if lower == "status":
            _print_block("Status", _status_text(env))
            continue
        if lower == "rooms":
            rooms = sorted(name for name, item in env.items.items() if item.level == 1)
            _print_block("Rooms", "\n".join(rooms) or "(none)")
            continue
        if lower == "visible":
            visible = sorted(env.agent.current_items.keys())
            _print_block("Visible", "\n".join(visible) or "(none)")
            continue
        if lower in {"inventory", "inv"}:
            inv = sorted(env.agent.inventory.keys())
            _print_block("Inventory", "\n".join(inv) or "(empty)")
            continue
        if lower == "task":
            _print_block("Task", f"{env.task}\n\nverify: {env.verify}")
            continue
        if lower == "actions":
            _print_block("Actions", "\n".join(sorted(env.actions)))
            continue
        if lower == "reset":
            obs, info = env.reset(seed=seed, options={"task": env.task})
            _apply_task(env, env.task, env.verify)
            _print_block("Observation", obs)
            continue
        if lower.startswith("newtask"):
            parts = lower.split()
            kind = parts[1] if len(parts) > 1 else (auto_task or "random")
            try:
                task, verify = _sample_task(env, kind)
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            _apply_task(env, task, verify)
            _print_block("Task", f"{task}\n\nverify: {verify}")
            _print_block("Observation", env._get_obs_natural())
            continue

        # Treat everything else as an environment action.
        obs, reward, terminated, truncated, info = env.step(raw)
        print(f"reward={reward:.1f}  terminated={terminated}  truncated={truncated}")
        _print_block("Observation", obs)
        if terminated or truncated:
            print("Episode finished. Type 'reset' to play again, or 'quit' to exit.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        env = create_env(args)
    except Exception as exc:  # noqa: BLE001 - surface friendly CLI errors
        print(f"Failed to create environment: {exc}", file=sys.stderr)
        return 1
    try:
        return run_repl(env, seed=args.seed, auto_task=args.auto_task)
    finally:
        env.close()


if __name__ == "__main__":
    raise SystemExit(main())
