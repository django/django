from ..exceptions import DataError


class Encoder:
    "Encode strings to bytes-like and decode bytes-like to strings"

    __slots__ = "encoding", "encoding_errors", "decode_responses"

    def __init__(self, encoding, encoding_errors, decode_responses):
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.decode_responses = decode_responses

    def encode(self, value):
        "Return a bytestring or bytes-like representation of the value"
        if isinstance(value, (bytes, memoryview)):
            return value
        elif isinstance(value, bool):
            # special case bool since it is a subclass of int
            raise DataError(
                "Invalid input of type: 'bool'. Convert to a "
                "bytes, string, int or float first."
            )
        elif isinstance(value, (int, float)):
            value = repr(value).encode()
        elif not isinstance(value, str):
            # a value we don't know how to deal with. throw an error
            typename = type(value).__name__
            raise DataError(
                f"Invalid input of type: '{typename}'. "
                f"Convert to a bytes, string, int or float first."
            )
        if isinstance(value, str):
            value = value.encode(self.encoding, self.encoding_errors)
        return value

    def decode(self, value, force=False):
        "Return a unicode string from the bytes-like representation"
        if self.decode_responses or force:
            if isinstance(value, memoryview):
                value = value.tobytes()
            if isinstance(value, bytes):
                value = value.decode(self.encoding, self.encoding_errors)
        return value
