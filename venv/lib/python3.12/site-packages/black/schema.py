import importlib.resources
import json
from typing import Any


def get_schema(tool_name: str = "black") -> Any:
    """Get the stored complete schema for black's settings."""
    assert tool_name == "black", "Only black is supported."

    pkg = "black.resources"
    fname = "black.schema.json"

    schema = importlib.resources.files(pkg).joinpath(fname)
    with schema.open(encoding="utf-8") as f:
        return json.load(f)
