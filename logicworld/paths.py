"""Path helpers for packaged scene data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def get_data_dir(data_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return the directory that stores scene JSONL files."""
    if data_dir is not None:
        return Path(data_dir)
    env_value = __import__("os").environ.get("LOGICWORLD_DATA_DIR", "").strip()
    if env_value:
        return Path(env_value)
    return DEFAULT_DATA_DIR


def default_scene_path(split: str = "test", data_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return path to ``train.jsonl`` or ``test.jsonl``."""
    if split not in {"train", "test"}:
        raise ValueError(f"Unknown split '{split}'. Expected 'train' or 'test'.")
    path = get_data_dir(data_dir) / f"{split}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Scene dataset not found: {path}. "
            "Set LOGICWORLD_DATA_DIR or pass scene_data explicitly."
        )
    return path


@lru_cache(maxsize=4)
def load_scene_dataset(
    split: str = "test",
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load all household scenes for a split into memory."""
    path = default_scene_path(split=split, data_dir=data_dir)
    scenes: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                scenes.append(json.loads(line))
    return scenes


def load_scene(
    house: Union[str, int],
    split: Optional[str] = None,
    data_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Load a single scene by house id (e.g. ``house_12`` or ``12``)."""
    house_str = str(house)
    if split is None:
        split = "train" if house_str.startswith("train") else "test"
    idx = int(house_str.split("_")[-1])
    scenes = load_scene_dataset(split=split, data_dir=str(data_dir) if data_dir else None)
    if idx < 0 or idx >= len(scenes):
        raise IndexError(f"House index {idx} out of range for split '{split}' ({len(scenes)} scenes).")
    return scenes[idx]
