from __future__ import unicode_literals
from asgiref.conformance import make_tests
from ..database_layer import DatabaseChannelLayer

channel_layer = DatabaseChannelLayer(expiry=1)
DatabaseLayerTests = make_tests(channel_layer, expiry_delay=1.1)
