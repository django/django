# -*- coding: utf-8 -*-
# !/usr/bin/env python

import unittest

from django.db import connection
from django.utils.url_config import configure_db

GENERIC_TESTS = [
    (
        'username:password@domain/database',
        ('username', 'password', 'domain', '', 'database', {})
    ),
    (
        'username:password@domain:123/database',
        ('username', 'password', 'domain', 123, 'database', {})
    ),
    (
        'domain:123/database',
        ('', '', 'domain', 123, 'database', {})
    ),
    (
        'user@domain:123/database',
        ('user', '', 'domain', 123, 'database', {})
    ),
    (
        'username:password@[2001:db8:1234::1234:5678:90af]:123/database',
        ('username', 'password', '2001:db8:1234::1234:5678:90af', 123, 'database', {})
    ),
    (
        'username:password@host:123/database?reconnect=true',
        ('username', 'password', 'host', 123, 'database', {'reconnect': True})
    ),
    (
        'username:password@/database',
        ('username', 'password', '', '', 'database', {})
    ),
]


class BaseURLTests:
    SCHEME = None
    STRING_PORTS = False  # Workaround for Oracle

    def test_parsing(self):
        for value, (user, passw, host, port, database, options) in GENERIC_TESTS:
            value = '{scheme}://{value}'.format(scheme=self.SCHEME, value=value)

            with self.subTest(value=value):
                result = configure_db(value)
                self.assertEqual(result['NAME'], database)
                self.assertEqual(result['HOST'], host)
                self.assertEqual(result['USER'], user)
                self.assertEqual(result['PASSWORD'], passw)
                self.assertEqual(result['PORT'], port if not self.STRING_PORTS else str(port))
                self.assertDictEqual(result['OPTIONS'], options)


@unittest.skipUnless(connection.vendor == 'sqlite', 'Sqlite tests')
class SqliteTests(BaseURLTests, unittest.TestCase):
    SCHEME = 'sqlite'

    def test_empty_url(self):
        url = 'sqlite://'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')

    def test_memory_url(self):
        url = 'sqlite://:memory:'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')


@unittest.skipUnless(connection.vendor == 'postgresql', 'Postgres tests')
class PostgresTests(BaseURLTests, unittest.TestCase):
    SCHEME = 'postgres'

    def test_unix_socket_parsing(self):
        url = 'postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], '/var/run/postgresql')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

        url = 'postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['HOST'], '/Users/postgres/RuN')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

    def test_search_path_parsing(self):
        url = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
               '/d8r82722r2kuvn?currentSchema=otherschema')
        url = configure_db(url)
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])

    def test_parsing_with_special_characters(self):
        url = 'postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], '#database')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], '#user')
        self.assertEqual(url['PASSWORD'], '#password')
        self.assertEqual(url['PORT'], 5431)

    def test_database_url_with_options(self):
        # Test full options
        url = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg'
               '@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
               '?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full')
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS'], {
            'sslrootcert': 'rds-combined-ca-bundle.pem',
            'sslmode': 'verify-full'
        })

    def test_gis_search_path_parsing(self):
        url = ('postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
               '/d8r82722r2kuvn?currentSchema=otherschema')
        url = configure_db(url)
        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.postgis')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])


@unittest.skipUnless(connection.vendor == 'mysql', 'Mysql tests')
class MysqlTests(BaseURLTests, unittest.TestCase):
    SCHEME = 'mysql'

    def test_with_sslca_options(self):
        url = 'mysql://uf07k1i6d8ia0v:wegauwhgeuioweg' \
              '@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn' \
              '?ssl-ca=rds-combined-ca-bundle.pem'
        url = configure_db(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 3306)
        self.assertEqual(url['OPTIONS'], {
            'ssl': {
                'ca': 'rds-combined-ca-bundle.pem'
            }
        })


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle Tests')
class OracleTests(BaseURLTests, unittest.TestCase):
    SCHEME = 'oracle'
    STRING_PORTS = True

    def test_dsn_parsing(self):
        dsn = (
            '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)'
            '(HOST=oraclehost)(PORT=1521)))'
            '(CONNECT_DATA=(SID=hr)))'
        )

        url = configure_db('oracle://scott:tiger@/' + dsn)

        self.assertEqual(url['ENGINE'], 'django.db.backends.oracle')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['HOST'], '')
        self.assertEqual(url['PORT'], '')

        url = configure_db(dsn)

        self.assertEqual(url['NAME'], dsn)
