"""Load item / receptacle configuration from JSON."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_ITEMS_CONFIG = PACKAGE_ROOT / "configs" / "items.json"


@lru_cache(maxsize=4)
def load_items_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load item attribute configuration.

    Resolution order:
    1. Explicit ``path`` argument
    2. ``LOGICWORLD_ITEMS_CONFIG`` environment variable
    3. Packaged default ``logicworld/configs/items.json``
    """
    if path is None:
        path = os.environ.get("LOGICWORLD_ITEMS_CONFIG", "").strip() or None
    config_path = Path(path) if path else DEFAULT_ITEMS_CONFIG
    if not config_path.exists():
        raise FileNotFoundError(f"Items config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    required = {"item_attributes", "receptacle_to_items", "max_pickup_num"}
    missing = required - set(data)
    if missing:
        raise KeyError(f"Items config missing keys: {sorted(missing)}")
    return data


def reload_items_config(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Clear cache and reload configuration (useful in tests / notebooks)."""
    load_items_config.cache_clear()
    return load_items_config(str(path) if path else None)


_CONFIG = load_items_config()

ITEM_ATTRIBUTES: Dict[str, Dict[str, bool]] = _CONFIG["item_attributes"]
RECEPTACLE_TO_ITEMS: Dict[str, list] = _CONFIG["receptacle_to_items"]
MAX_PICKUP_NUM: int = int(_CONFIG["max_pickup_num"])

# Backward-compatible alias used by env.py
receptacle2ITEMS = RECEPTACLE_TO_ITEMS
