"""Basic smoke tests for LOGICWorld packaging."""

from __future__ import annotations

import gymnasium as gym
import pytest

import logicworld  # noqa: F401
from logicworld import LOGICWorldEnv, load_scene


@pytest.fixture(scope="module")
def scene():
    return load_scene("house_0", split="test")


def test_import_and_version():
    assert logicworld.__version__


def test_items_config_loaded():
    assert "apple" in logicworld.ITEM_ATTRIBUTES
    assert logicworld.ITEM_ATTRIBUTES["apple"]["pickable"] is True
    assert "fridge" in logicworld.RECEPTACLE_TO_ITEMS
    assert logicworld.MAX_PICKUP_NUM >= 1


def test_load_scene(scene):
    assert "rooms" in scene
    assert "objects" in scene


def test_task_generator_basic(scene):
    env = LOGICWorldEnv(house="house_0", scene_data=scene, task={})
    env.reset(seed=0)
    task, verify = env.task_generator.create_visited_item_task(1)
    assert isinstance(task, str)
    assert isinstance(verify, str)
    # Env keeps thin wrappers for convenience
    task2, verify2 = env.create_pickup_item_task(1)
    assert isinstance(task2, str)


def test_env_reset_step(scene):
    env = LOGICWorldEnv(
        house="house_0",
        scene_data=scene,
        task={"task": "demo", "verify": "True"},
    )
    obs, info = env.reset(seed=0)
    assert isinstance(obs, str)
    assert "ENVIRONMENT" in obs or len(obs) > 0

    rooms = [name for name, item in env.items.items() if item.level == 1]
    assert rooms
    obs, reward, terminated, truncated, info = env.step(f"NAVIGATE_TO('{rooms[0]}')")
    assert isinstance(obs, str)
    assert isinstance(reward, float)
    assert terminated is False or terminated is True
    env.close()


def test_cli_help():
    from logicworld.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_create_env_and_step(scene):
    from logicworld.cli import build_parser, create_env

    args = build_parser().parse_args(["--house", "0", "--split", "test", "--seed", "0"])
    env = create_env(args)
    obs, info = env.reset(seed=0)
    assert isinstance(obs, str)
    rooms = [name for name, item in env.items.items() if item.level == 1]
    obs, reward, terminated, truncated, info = env.step(f"NAVIGATE_TO('{rooms[0]}')")
    assert isinstance(reward, float)
    env.close()
