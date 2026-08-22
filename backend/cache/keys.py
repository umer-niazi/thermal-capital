"""Deterministic cache key generation for FortyGuard API requests."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonicalize(obj: Any) -> Any:
    """Recursively canonicalize nested dictionaries, lists, and numbers for deterministic hashing."""
    if isinstance(obj, dict):
        # Exclude any API keys or secret fields if present
        clean_dict = {
            str(k): _canonicalize(v)
            for k, v in obj.items()
            if k.lower() not in ("api_key", "api-key", "authorization", "secret")
        }
        return {k: clean_dict[k] for k in sorted(clean_dict.keys())}
    elif isinstance(obj, list):
        return [_canonicalize(item) for item in obj]
    elif isinstance(obj, float):
        # Round floats to 6 decimal places to avoid microscopic floating point differences
        return round(obj, 6)
    return obj


def generate_cache_key(endpoint: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> str:
    """Generate a deterministic SHA-256 cache key for an API endpoint and request parameters.

    Parameters
    ----------
    endpoint:
        The API route string (e.g. "/v1/heatmap", "/v1/env_params").
    payload:
        Optional request body payload dictionary.
    kwargs:
        Additional query or route parameters.

    Returns
    -------
    str
        64-character hex SHA-256 digest representing the unique canonical request.
    """
    merged_data: dict[str, Any] = {}
    if payload:
        merged_data.update(payload)
    if kwargs:
        merged_data.update(kwargs)

    canonical_obj = {
        "endpoint": endpoint.strip().lower(),
        "params": _canonicalize(merged_data),
    }

    serialized = json.dumps(
        canonical_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
