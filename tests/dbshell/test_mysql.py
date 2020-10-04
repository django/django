from django.db.backends.mysql.client import DatabaseClient
from django.test import SimpleTestCase


class MySqlDbshellCommandTestCase(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None):
        if parameters is None:
            parameters = []
        return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_fails_with_keyerror_on_incomplete_config(self):
        with self.assertRaises(KeyError):
            self.settings_to_cmd_args_env({})

    def test_basic_params_specified_in_settings(self):
        expected_args = [
            'mysql',
            '--user=someuser',
            '--password=somepassword',
            '--host=somehost',
            '--port=444',
            'somedbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {},
            }),
            (expected_args, expected_env),
        )

    def test_options_override_settings_proper_values(self):
        settings_port = 444
        options_port = 555
        self.assertNotEqual(settings_port, options_port, 'test pre-req')
        expected_args = [
            'mysql',
            '--user=optionuser',
            '--password=optionpassword',
            '--host=optionhost',
            '--port=%s' % options_port,
            'optiondbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'settingdbname',
                'USER': 'settinguser',
                'PASSWORD': 'settingpassword',
                'HOST': 'settinghost',
                'PORT': settings_port,
                'OPTIONS': {
                    'db': 'optiondbname',
                    'user': 'optionuser',
                    'passwd': 'optionpassword',
                    'host': 'optionhost',
                    'port': options_port,
                },
            }),
            (expected_args, expected_env),
        )

    def test_options_password(self):
        expected_args = [
            'mysql',
            '--user=someuser',
            '--password=optionpassword',
            '--host=somehost',
            '--port=444',
            'somedbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'settingpassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {'password': 'optionpassword'},
            }),
            (expected_args, expected_env),
        )

    def test_options_charset(self):
        expected_args = [
            'mysql',
            '--user=someuser',
            '--password=somepassword',
            '--host=somehost',
            '--port=444',
            '--default-character-set=utf8',
            'somedbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {'charset': 'utf8'},
            }),
            (expected_args, expected_env),
        )

    def test_can_connect_using_sockets(self):
        expected_args = [
            'mysql',
            '--user=someuser',
            '--password=somepassword',
            '--socket=/path/to/mysql.socket.file',
            'somedbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': '/path/to/mysql.socket.file',
                'PORT': None,
                'OPTIONS': {},
            }),
            (expected_args, expected_env),
        )

    def test_ssl_certificate_is_added(self):
        expected_args = [
            'mysql',
            '--user=someuser',
            '--password=somepassword',
            '--host=somehost',
            '--port=444',
            '--ssl-ca=sslca',
            '--ssl-cert=sslcert',
            '--ssl-key=sslkey',
            'somedbname',
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {
                    'ssl': {
                        'ca': 'sslca',
                        'cert': 'sslcert',
                        'key': 'sslkey',
                    },
                },
            }),
            (expected_args, expected_env),
        )

    def test_parameters(self):
        self.assertEqual(
            self.settings_to_cmd_args_env(
                {
                    'NAME': 'somedbname',
                    'USER': None,
                    'PASSWORD': None,
                    'HOST': None,
                    'PORT': None,
                    'OPTIONS': {},
                },
                ['--help'],
            ),
            (['mysql', 'somedbname', '--help'], None),
        )
