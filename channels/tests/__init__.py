import warnings

warnings.warn(
    "channels.tests package is deprecated. Use channels.test",
    DeprecationWarning,
)

from channels.test.base import TransactionChannelTestCase, ChannelTestCase, Client, apply_routes  # NOQA isort:skip
from channels.test.http import HttpClient  # NOQA isort:skip
