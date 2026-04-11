"""
_ssl_compat.py
websocket - WebSocket client library for Python

Copyright 2025 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ssl as _ssl_module
    from ssl import (
        SSLError as _SSLErrorType,
        SSLEOFError as _SSLEOFErrorType,
        SSLWantReadError as _SSLWantReadErrorType,
        SSLWantWriteError as _SSLWantWriteErrorType,
    )
else:
    _ssl_module = None
    _SSLErrorType = None
    _SSLEOFErrorType = None
    _SSLWantReadErrorType = None
    _SSLWantWriteErrorType = None

__all__ = [
    "HAVE_SSL",
    "ssl",
    "SSLError",
    "SSLEOFError",
    "SSLWantReadError",
    "SSLWantWriteError",
]

try:
    import ssl
    from ssl import SSLError, SSLEOFError, SSLWantReadError, SSLWantWriteError  # type: ignore[attr-defined]

    HAVE_SSL = True
except ImportError:
    # dummy class of SSLError for environment without ssl support
    class SSLError(Exception):  # type: ignore[no-redef]
        pass

    class SSLEOFError(Exception):  # type: ignore[no-redef]
        pass

    class SSLWantReadError(Exception):  # type: ignore[no-redef]
        pass

    class SSLWantWriteError(Exception):  # type: ignore[no-redef]
        pass

    ssl = None  # type: ignore[assignment,no-redef]
    HAVE_SSL = False
