from typing import Any


class ProfileInformation:
    """
    Wrapper around FT.PROFILE response
    """

    def __init__(self, info: Any) -> None:
        self._info: Any = info

    @property
    def info(self) -> Any:
        return self._info
