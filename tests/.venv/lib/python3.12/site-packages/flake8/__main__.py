"""Module allowing for ``python -m flake8 ...``."""

from __future__ import annotations

from flake8.main.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
