"""LOGICWorld: a logic-conditioned household robot benchmark environment."""

from __future__ import annotations

from gymnasium.envs.registration import register

from logicworld.config import ITEM_ATTRIBUTES, MAX_PICKUP_NUM, RECEPTACLE_TO_ITEMS
from logicworld.env import Agent, Item, LOGICWorldEnv, UserAgent
from logicworld.paths import load_scene, load_scene_dataset
from logicworld.tasks import TaskGenerator

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "ITEM_ATTRIBUTES",
    "Item",
    "LOGICWorldEnv",
    "MAX_PICKUP_NUM",
    "RECEPTACLE_TO_ITEMS",
    "TaskGenerator",
    "UserAgent",
    "load_scene",
    "load_scene_dataset",
    "__version__",
]

# Gymnasium environment ids
register(
    id="LOGICWorld-v0",
    entry_point="logicworld.env:LOGICWorldEnv",
    max_episode_steps=100,
)
