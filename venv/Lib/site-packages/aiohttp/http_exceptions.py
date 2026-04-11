"""Low-level http related exceptions."""

from textwrap import indent
from typing import Optional, Union

from .typedefs import _CIMultiDict

__all__ = ("HttpProcessingError",)


class HttpProcessingError(Exception):
    """HTTP error.

    Shortcut for raising HTTP errors with custom code, message and headers.

    code: HTTP Error code.
    message: (optional) Error message.
    headers: (optional) Headers to be sent in response, a list of pairs
    """

    code = 0
    message = ""
    headers = None

    def __init__(
        self,
        *,
        code: Optional[int] = None,
        message: str = "",
        headers: Optional[_CIMultiDict] = None,
    ) -> None:
        if code is not None:
            self.code = code
        self.headers = headers
        self.message = message

    def __str__(self) -> str:
        msg = indent(self.message, "  ")
        return f"{self.code}, message:\n{msg}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.code}, message={self.message!r}>"


class BadHttpMessage(HttpProcessingError):

    code = 400
    message = "Bad Request"

    def __init__(self, message: str, *, headers: Optional[_CIMultiDict] = None) -> None:
        super().__init__(message=message, headers=headers)
        self.args = (message,)


class HttpBadRequest(BadHttpMessage):

    code = 400
    message = "Bad Request"


class PayloadEncodingError(BadHttpMessage):
    """Base class for payload errors"""


class ContentEncodingError(PayloadEncodingError):
    """Content encoding error."""


class TransferEncodingError(PayloadEncodingError):
    """transfer encoding error."""


class ContentLengthError(PayloadEncodingError):
    """Not enough data to satisfy content length header."""


class DecompressSizeError(PayloadEncodingError):
    """Decompressed size exceeds the configured limit."""


class LineTooLong(BadHttpMessage):
    def __init__(
        self, line: str, limit: str = "Unknown", actual_size: str = "Unknown"
    ) -> None:
        super().__init__(
            f"Got more than {limit} bytes ({actual_size}) when reading {line}."
        )
        self.args = (line, limit, actual_size)


class InvalidHeader(BadHttpMessage):
    def __init__(self, hdr: Union[bytes, str]) -> None:
        hdr_s = hdr.decode(errors="backslashreplace") if isinstance(hdr, bytes) else hdr
        super().__init__(f"Invalid HTTP header: {hdr!r}")
        self.hdr = hdr_s
        self.args = (hdr,)


class BadStatusLine(BadHttpMessage):
    def __init__(self, line: str = "", error: Optional[str] = None) -> None:
        if not isinstance(line, str):
            line = repr(line)
        super().__init__(error or f"Bad status line {line!r}")
        self.args = (line,)
        self.line = line


class BadHttpMethod(BadStatusLine):
    """Invalid HTTP method in status line."""

    def __init__(self, line: str = "", error: Optional[str] = None) -> None:
        super().__init__(line, error or f"Bad HTTP method in status line {line!r}")


class InvalidURLError(BadHttpMessage):
    pass
