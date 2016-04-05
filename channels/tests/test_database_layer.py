from __future__ import unicode_literals
from asgiref.conformance import ConformanceTestCase
from channels.database_layer import DatabaseChannelLayer


class DatabaseLayerTests(ConformanceTestCase):
    channel_layer = DatabaseChannelLayer(expiry=1, group_expiry=3)
    expiry_delay = 2.1
