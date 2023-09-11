from logging import getLogger
from typing import Any, Union

from ..exceptions import ConnectionError, InvalidResponse, ResponseError
from ..typing import EncodableT
from .base import _AsyncRESPBase, _RESPBase
from .socket import SERVER_CLOSED_CONNECTION_ERROR


class _RESP3Parser(_RESPBase):
    """RESP3 protocol implementation"""

    def __init__(self, socket_read_size):
        super().__init__(socket_read_size)
        self.push_handler_func = self.handle_push_response

    def handle_push_response(self, response):
        logger = getLogger("push_response")
        logger.info("Push response: " + str(response))
        return response

    def read_response(self, disable_decoding=False, push_request=False):
        pos = self._buffer.get_pos() if self._buffer else None
        try:
            result = self._read_response(
                disable_decoding=disable_decoding, push_request=push_request
            )
        except BaseException:
            if self._buffer:
                self._buffer.rewind(pos)
            raise
        else:
            self._buffer.purge()
            return result

    def _read_response(self, disable_decoding=False, push_request=False):
        raw = self._buffer.readline()
        if not raw:
            raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)

        byte, response = raw[:1], raw[1:]

        # server returned an error
        if byte in (b"-", b"!"):
            if byte == b"!":
                response = self._buffer.read(int(response))
            response = response.decode("utf-8", errors="replace")
            error = self.parse_error(response)
            # if the error is a ConnectionError, raise immediately so the user
            # is notified
            if isinstance(error, ConnectionError):
                raise error
            # otherwise, we're dealing with a ResponseError that might belong
            # inside a pipeline response. the connection's read_response()
            # and/or the pipeline's execute() will raise this error if
            # necessary, so just return the exception instance here.
            return error
        # single value
        elif byte == b"+":
            pass
        # null value
        elif byte == b"_":
            return None
        # int and big int values
        elif byte in (b":", b"("):
            return int(response)
        # double value
        elif byte == b",":
            return float(response)
        # bool value
        elif byte == b"#":
            return response == b"t"
        # bulk response
        elif byte == b"$":
            response = self._buffer.read(int(response))
        # verbatim string response
        elif byte == b"=":
            response = self._buffer.read(int(response))[4:]
        # array response
        elif byte == b"*":
            response = [
                self._read_response(disable_decoding=disable_decoding)
                for _ in range(int(response))
            ]
        # set response
        elif byte == b"~":
            # redis can return unhashable types (like dict) in a set,
            # so we need to first convert to a list, and then try to convert it to a set
            response = [
                self._read_response(disable_decoding=disable_decoding)
                for _ in range(int(response))
            ]
            try:
                response = set(response)
            except TypeError:
                pass
        # map response
        elif byte == b"%":
            # we use this approach and not dict comprehension here
            # because this dict comprehension fails in python 3.7
            resp_dict = {}
            for _ in range(int(response)):
                key = self._read_response(disable_decoding=disable_decoding)
                resp_dict[key] = self._read_response(
                    disable_decoding=disable_decoding, push_request=push_request
                )
            response = resp_dict
        # push response
        elif byte == b">":
            response = [
                self._read_response(
                    disable_decoding=disable_decoding, push_request=push_request
                )
                for _ in range(int(response))
            ]
            res = self.push_handler_func(response)
            if not push_request:
                return self._read_response(
                    disable_decoding=disable_decoding, push_request=push_request
                )
            else:
                return res
        else:
            raise InvalidResponse(f"Protocol Error: {raw!r}")

        if isinstance(response, bytes) and disable_decoding is False:
            response = self.encoder.decode(response)
        return response

    def set_push_handler(self, push_handler_func):
        self.push_handler_func = push_handler_func


class _AsyncRESP3Parser(_AsyncRESPBase):
    def __init__(self, socket_read_size):
        super().__init__(socket_read_size)
        self.push_handler_func = self.handle_push_response

    def handle_push_response(self, response):
        logger = getLogger("push_response")
        logger.info("Push response: " + str(response))
        return response

    async def read_response(
        self, disable_decoding: bool = False, push_request: bool = False
    ):
        if self._chunks:
            # augment parsing buffer with previously read data
            self._buffer += b"".join(self._chunks)
            self._chunks.clear()
        self._pos = 0
        response = await self._read_response(
            disable_decoding=disable_decoding, push_request=push_request
        )
        # Successfully parsing a response allows us to clear our parsing buffer
        self._clear()
        return response

    async def _read_response(
        self, disable_decoding: bool = False, push_request: bool = False
    ) -> Union[EncodableT, ResponseError, None]:
        if not self._stream or not self.encoder:
            raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
        raw = await self._readline()
        response: Any
        byte, response = raw[:1], raw[1:]

        # if byte not in (b"-", b"+", b":", b"$", b"*"):
        #     raise InvalidResponse(f"Protocol Error: {raw!r}")

        # server returned an error
        if byte in (b"-", b"!"):
            if byte == b"!":
                response = await self._read(int(response))
            response = response.decode("utf-8", errors="replace")
            error = self.parse_error(response)
            # if the error is a ConnectionError, raise immediately so the user
            # is notified
            if isinstance(error, ConnectionError):
                self._clear()  # Successful parse
                raise error
            # otherwise, we're dealing with a ResponseError that might belong
            # inside a pipeline response. the connection's read_response()
            # and/or the pipeline's execute() will raise this error if
            # necessary, so just return the exception instance here.
            return error
        # single value
        elif byte == b"+":
            pass
        # null value
        elif byte == b"_":
            return None
        # int and big int values
        elif byte in (b":", b"("):
            return int(response)
        # double value
        elif byte == b",":
            return float(response)
        # bool value
        elif byte == b"#":
            return response == b"t"
        # bulk response
        elif byte == b"$":
            response = await self._read(int(response))
        # verbatim string response
        elif byte == b"=":
            response = (await self._read(int(response)))[4:]
        # array response
        elif byte == b"*":
            response = [
                (await self._read_response(disable_decoding=disable_decoding))
                for _ in range(int(response))
            ]
        # set response
        elif byte == b"~":
            # redis can return unhashable types (like dict) in a set,
            # so we need to first convert to a list, and then try to convert it to a set
            response = [
                (await self._read_response(disable_decoding=disable_decoding))
                for _ in range(int(response))
            ]
            try:
                response = set(response)
            except TypeError:
                pass
        # map response
        elif byte == b"%":
            response = {
                (await self._read_response(disable_decoding=disable_decoding)): (
                    await self._read_response(disable_decoding=disable_decoding)
                )
                for _ in range(int(response))
            }
        # push response
        elif byte == b">":
            response = [
                (
                    await self._read_response(
                        disable_decoding=disable_decoding, push_request=push_request
                    )
                )
                for _ in range(int(response))
            ]
            res = self.push_handler_func(response)
            if not push_request:
                return await (
                    self._read_response(
                        disable_decoding=disable_decoding, push_request=push_request
                    )
                )
            else:
                return res
        else:
            raise InvalidResponse(f"Protocol Error: {raw!r}")

        if isinstance(response, bytes) and disable_decoding is False:
            response = self.encoder.decode(response)
        return response

    def set_push_handler(self, push_handler_func):
        self.push_handler_func = push_handler_func
