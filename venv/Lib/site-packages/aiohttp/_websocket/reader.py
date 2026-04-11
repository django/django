"""Reader for WebSocket protocol versions 13 and 8."""

from typing import TYPE_CHECKING

from ..helpers import NO_EXTENSIONS

if TYPE_CHECKING or NO_EXTENSIONS:  # pragma: no cover
    from .reader_py import (
        WebSocketDataQueue as WebSocketDataQueuePython,
        WebSocketReader as WebSocketReaderPython,
    )

    WebSocketReader = WebSocketReaderPython
    WebSocketDataQueue = WebSocketDataQueuePython
else:
    try:
        from .reader_c import (  # type: ignore[import-not-found]
            WebSocketDataQueue as WebSocketDataQueueCython,
            WebSocketReader as WebSocketReaderCython,
        )

        WebSocketReader = WebSocketReaderCython
        WebSocketDataQueue = WebSocketDataQueueCython
    except ImportError:  # pragma: no cover
        from .reader_py import (
            WebSocketDataQueue as WebSocketDataQueuePython,
            WebSocketReader as WebSocketReaderPython,
        )

        WebSocketReader = WebSocketReaderPython
        WebSocketDataQueue = WebSocketDataQueuePython
