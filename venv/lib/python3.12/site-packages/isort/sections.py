"""Defines all sections isort uses by default"""

from typing import Tuple

FUTURE: str = "FUTURE"
STDLIB: str = "STDLIB"
THIRDPARTY: str = "THIRDPARTY"
FIRSTPARTY: str = "FIRSTPARTY"
LOCALFOLDER: str = "LOCALFOLDER"
DEFAULT: Tuple[str, ...] = (FUTURE, STDLIB, THIRDPARTY, FIRSTPARTY, LOCALFOLDER)
