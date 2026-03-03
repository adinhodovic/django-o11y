"""Dict deep-merge utility."""

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Deep-merge *override* into *base* in place.

    For each key in *override*: if both values are dicts, recurse; otherwise
    overwrite the value in *base*.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
