"""JSON serialization helpers.

Recursively converts values into JSON-safe primitives (datetimes -> ISO 8601
strings) so anything can be stored in JSON/JSONB columns or returned by the API.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)
