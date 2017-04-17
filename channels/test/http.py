import warnings

warnings.warn(
    "test.http.HttpClient is deprecated. Use test.websocket.WSClient",
    DeprecationWarning,
)

from .websocket import WSClient as HttpClient  # NOQA isort:skip
