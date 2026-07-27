#!/usr/bin/env python3
"""Generate conditional / logical tasks from household scenes."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from logicworld import LOGICWorldEnv
from logicworld.paths import load_scene_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--min-rooms", type=int, default=3)
    parser.add_argument("--max-rooms", type=int, default=10)
    parser.add_argument("--task-num", type=int, default=2)
    parser.add_argument("--t-atom-num", type=int, default=1)
    parser.add_argument("--l-atom-num", type=int, default=2)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/conditional.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max houses to process (0 = all)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenes = load_scene_dataset(args.split)
    room_count2house_num: dict[int, list[int]] = defaultdict(list)
    for i, scene in enumerate(scenes):
        room_count2house_num[len(scene["rooms"])].append(i)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.output.open("w", encoding="utf-8") as out:
        for room_count in range(args.min_rooms, args.max_rooms + 1):
            for house_num in tqdm(room_count2house_num[room_count], desc=f"rooms={room_count}"):
                if args.limit and written >= args.limit:
                    break
                env = LOGICWorldEnv(
                    house=f"house_{house_num}",
                    scene_data=scenes[house_num],
                    task={},
                )
                task, verify = env.task_generator.random_generate_logic_expression(
                    task_num=args.task_num,
                    t_atom_num=args.t_atom_num,
                    l_atom_num=args.l_atom_num,
                )
                record = {
                    "house": f"{args.split}-house_{house_num}",
                    "task_type": "conditional",
                    "task": task,
                    "verify": verify,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
            if args.limit and written >= args.limit:
                break

    print(f"Wrote {written} tasks to {args.output}")


if __name__ == "__main__":
    main()
