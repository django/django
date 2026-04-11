import json

from redis._parsers.helpers import pairs_to_dict
from redis.commands.vectorset.utils import (
    parse_vemb_result,
    parse_vlinks_result,
    parse_vsim_result,
)

from ..helpers import get_protocol_version
from .commands import (
    VEMB_CMD,
    VGETATTR_CMD,
    VINFO_CMD,
    VLINKS_CMD,
    VSIM_CMD,
    VectorSetCommands,
)


class VectorSet(VectorSetCommands):
    def __init__(self, client, **kwargs):
        """Create a new VectorSet client."""
        # Set the module commands' callbacks
        self._MODULE_CALLBACKS = {
            VEMB_CMD: parse_vemb_result,
            VSIM_CMD: parse_vsim_result,
            VGETATTR_CMD: lambda r: r and json.loads(r) or None,
        }

        self._RESP2_MODULE_CALLBACKS = {
            VINFO_CMD: lambda r: r and pairs_to_dict(r) or None,
            VLINKS_CMD: parse_vlinks_result,
        }
        self._RESP3_MODULE_CALLBACKS = {}

        self.client = client
        self.execute_command = client.execute_command

        if get_protocol_version(self.client) in ["3", 3]:
            self._MODULE_CALLBACKS.update(self._RESP3_MODULE_CALLBACKS)
        else:
            self._MODULE_CALLBACKS.update(self._RESP2_MODULE_CALLBACKS)

        for k, v in self._MODULE_CALLBACKS.items():
            self.client.set_response_callback(k, v)
