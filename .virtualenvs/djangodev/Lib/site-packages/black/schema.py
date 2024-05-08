import importlib.resources
import json
import sys
from typing import Any


def get_schema(tool_name: str = "black") -> Any:
    """Get the stored complete schema for black's settings."""
    assert tool_name == "black", "Only black is supported."

    pkg = "black.resources"
    fname = "black.schema.json"

    if sys.version_info < (3, 9):
        with importlib.resources.open_text(pkg, fname, encoding="utf-8") as f:
            return json.load(f)

    schema = importlib.resources.files(pkg).joinpath(fname)  # type: ignore[unreachable]
    with schema.open(encoding="utf-8") as f:
        return json.load(f)
