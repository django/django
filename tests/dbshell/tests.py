import os

from django.db.backends.mysql.client import DatabaseClient as MySQLDatabaseClient
from django.db.backends.postgresql_psycopg2.client import DatabaseClient as PostgresDatabaseClient
from django.test import SimpleTestCase


class MySqlDbshellCommandTestCase(SimpleTestCase):

    def test_fails_with_keyerror_on_incomplete_config(self):
        with self.assertRaises(KeyError):
            self.get_command_line_arguments({})

    def test_basic_params_specified_in_settings(self):
        self.assertEqual(
            ['mysql', '--user=someuser', '--password=somepassword',
             '--host=somehost', '--port=444', 'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {},
            }))

    def test_options_override_settings_proper_values(self):
        settings_port = 444
        options_port = 555
        self.assertNotEqual(settings_port, options_port, 'test pre-req')
        self.assertEqual(
            ['mysql', '--user=optionuser', '--password=optionpassword',
             '--host=optionhost', '--port={}'.format(options_port), 'optiondbname'],
            self.get_command_line_arguments({
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
            }))

    def test_can_connect_using_sockets(self):
        self.assertEqual(
            ['mysql', '--user=someuser', '--password=somepassword',
             '--socket=/path/to/mysql.socket.file', 'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': '/path/to/mysql.socket.file',
                'PORT': None,
                'OPTIONS': {},
            }))

    def test_ssl_certificate_is_added(self):
        self.assertEqual(
            ['mysql', '--user=someuser', '--password=somepassword',
             '--host=somehost', '--port=444', '--ssl-ca=sslca', 'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {'ssl': {'ca': 'sslca'}},
            }))

    def get_command_line_arguments(self, connection_settings):
        return MySQLDatabaseClient.settings_to_cmd_args(connection_settings)


class PostgresDbshellCommandTestCase(SimpleTestCase):

    def test_fails_with_keyerror_on_incomplete_config(self):
        with self.assertRaises(KeyError):
            self.get_command_line_arguments({})

    def test_basic_params_specified_in_settings(self):
        self.assertEqual(
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444',
             'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {},
            }))

    def test_options_override_settings_proper_values(self):
        self.assertEqual(
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444',
             'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'settingpassword',
                'HOST': 'somehost',
                'PORT': 444,
                'OPTIONS': {
                    "search_path": "my_other_schema,public"
                },
            }))
        self.assertEqual(os.environ['PGOPTIONS'], "-c search_path=my_other_schema,public")

    def test_can_connect_using_sockets(self):
        self.assertEqual(
            ['psql', '-U', 'someuser', '-h', '/path/to/psql.socket.file',
             'somedbname'],
            self.get_command_line_arguments({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': '/path/to/psql.socket.file',
                'PORT': None,
                'OPTIONS': {},
            }))

    def get_command_line_arguments(self, connection_settings):
        return PostgresDatabaseClient.settings_to_cmd_args(connection_settings)
