"""Support executing the CLI by doing `python -m pytokens`."""
from __future__ import annotations

from pytokens.cli import cli

if __name__ == "__main__":
    raise SystemExit(cli())
