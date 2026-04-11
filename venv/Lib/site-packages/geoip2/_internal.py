"""Internal utilities."""

import datetime
import json
from abc import ABCMeta
from typing import Any


class Model(metaclass=ABCMeta):  # noqa: B024
    """Shared methods for MaxMind model classes."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.to_dict() == other.to_dict()

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        # This is not particularly efficient, but I don't expect it to be used much.
        return hash(json.dumps(self.to_dict(), sort_keys=True))

    def to_dict(self) -> dict[str, Any]:  # noqa: C901, PLR0912
        """Return a dict of the object suitable for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "to_dict") and callable(value.to_dict):
                if d := value.to_dict():
                    result[key] = d
            elif isinstance(value, (list, tuple)):
                ls = []
                for e in value:
                    if hasattr(e, "to_dict") and callable(e.to_dict):
                        if e := e.to_dict():
                            ls.append(e)
                    elif e is not None:
                        ls.append(e)
                if ls:
                    result[key] = ls
            # We only have dicts of strings currently. Do not bother with
            # the general case.
            elif isinstance(value, dict):
                if value:
                    result[key] = value
            elif isinstance(value, datetime.date):
                result[key] = value.isoformat()
            elif value is not None and value is not False:
                result[key] = value

        # network and ip_address are properties for performance reasons
        if hasattr(self, "ip_address") and self.ip_address is not None:
            result["ip_address"] = str(self.ip_address)
        if hasattr(self, "network") and self.network is not None:
            result["network"] = str(self.network)

        return result
