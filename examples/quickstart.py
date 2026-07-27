#!/usr/bin/env python3
"""Minimal LOGICWorld usage example."""

from __future__ import annotations

import logicworld  # noqa: F401  # registers Gymnasium envs
from logicworld import LOGICWorldEnv, load_scene


def main() -> None:
    scene = load_scene("house_0", split="test")
    env = LOGICWorldEnv(
        house="house_0",
        scene_data=scene,
        task={
            "task": "Explore the house and call DONE when finished.",
            "verify": "True",
            "task_type": "demo",
        },
    )
    obs, info = env.reset(seed=42)
    print("Reset observation:")
    print(obs)
    print()

    rooms = [name for name, item in env.items.items() if item.level == 1]
    if rooms:
        target = rooms[0]
        action = f"NAVIGATE_TO('{target}')"
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Action: {action}")
        print(f"Reward: {reward} | terminated={terminated} truncated={truncated}")
        print(obs)

    env.close()


if __name__ == "__main__":
    main()
