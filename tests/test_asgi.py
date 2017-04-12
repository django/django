from channels import DEFAULT_CHANNEL_LAYER
from channels.asgi import InvalidChannelLayerError, channel_layers
from channels.test import ChannelTestCase
from django.test import override_settings


class TestChannelLayerManager(ChannelTestCase):

    def test_config_error(self):
        """
        If channel layer doesn't specify TEST_CONFIG, `make_test_backend`
        should result into error.
        """

        with self.assertRaises(InvalidChannelLayerError):
            channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    @override_settings(CHANNEL_LAYERS={
        'default': {
            'BACKEND': 'asgiref.inmemory.ChannelLayer',
            'ROUTING': [],
            'TEST_CONFIG': {
                'expiry': 100500,
            },
        },
    })
    def test_config_instance(self):
        """
        If channel layer provides TEST_CONFIG, `make_test_backend` should
        return channel layer instance appropriate for testing.
        """

        layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)
        self.assertEqual(layer.channel_layer.expiry, 100500)
