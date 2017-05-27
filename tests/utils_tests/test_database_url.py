# -*- coding: utf-8 -*-
# !/usr/bin/env python

import os
import unittest

from django.core.exceptions import ImproperlyConfigured
from django.utils.database_url import parse_from_environment, parse_url


class DatabaseTestSuite(unittest.TestCase):
    def test_postgres_parsing(self):
        url = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@'
               'ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn')
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_postgres_unix_socket_parsing(self):
        url = 'postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], '/var/run/postgresql')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

        url = 'postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['HOST'], '/Users/postgres/RuN')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

    def test_ipv6_parsing(self):
        url = 'postgres://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], '2001:db8:1234::1234:5678:90af')
        self.assertEqual(url['USER'], 'ieRaekei9wilaim7')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_postgres_search_path_parsing(self):
        url = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
               '/d8r82722r2kuvn?currentSchema=otherschema')
        url = parse_url(url)
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])

    def test_postgres_parsing_with_special_characters(self):
        url = 'postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], '#database')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], '#user')
        self.assertEqual(url['PASSWORD'], '#password')
        self.assertEqual(url['PORT'], 5431)

    def test_postgis_parsing(self):
        url = 'postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.postgis')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_postgis_search_path_parsing(self):
        url = ('postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
               '/d8r82722r2kuvn?currentSchema=otherschema')
        url = parse_url(url)
        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.postgis')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])

    def test_mysql_gis_parsing(self):
        url = ('mysqlgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
               '/d8r82722r2kuvn')
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.mysql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_mysql_connector_parsing(self):
        url = ('mysql.connector.django://uf07k1i6d8ia0v:wegauwhgeuioweg'
               '@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn')
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'mysql.connector.django')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_cleardb_parsing(self):
        url = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(url['NAME'], 'heroku_97681db3eff7580')
        self.assertEqual(url['HOST'], 'us-cdbr-east.cleardb.com')
        self.assertEqual(url['USER'], 'bea6eb025ca0d8')
        self.assertEqual(url['PASSWORD'], '69772142')
        self.assertEqual(url['PORT'], '')

    def test_database_url(self):
        del os.environ['DATABASE_URL']
        with self.assertRaises(ImproperlyConfigured):
            parse_from_environment()

        os.environ['DATABASE_URL'] = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@'
                                      'ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn')

        url = parse_from_environment()['default']

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)

    def test_empty_sqlite_url(self):
        url = 'sqlite://'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')

    def test_memory_sqlite_url(self):
        url = 'sqlite://:memory:'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')

    def test_parse_engine_setting(self):
        engine = 'django_mysqlpool.backends.mysqlpool'
        url = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = parse_url(url, ENGINE=engine)

        self.assertEqual(url['ENGINE'], engine)

    def test_config_engine_setting(self):
        engine = 'django_mysqlpool.backends.mysqlpool'
        os.environ['DATABASE_URL'] = ('mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com'
                                      '/heroku_97681db3eff7580?reconnect=true')
        url = parse_from_environment(ENGINE=engine)['default']

        self.assertEqual(url['ENGINE'], engine)

    def test_parse_conn_max_age_setting(self):
        conn_max_age = 600
        url = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = parse_url(url, CONN_MAX_AGE=conn_max_age)

        self.assertEqual(url['CONN_MAX_AGE'], conn_max_age)

    def test_config_conn_max_age_setting(self):
        conn_max_age = 600
        os.environ['DATABASE_URL'] = ('mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com'
                                      '/heroku_97681db3eff7580?reconnect=true')
        url = parse_from_environment(CONN_MAX_AGE=conn_max_age)['default']

        self.assertEqual(url['CONN_MAX_AGE'], conn_max_age)

    def test_database_url_with_options(self):
        # Test full options
        os.environ['DATABASE_URL'] = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg'
                                      '@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
                                      '?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full')
        url = parse_from_environment()['default']

        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql_psycopg2')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS'], {
            'sslrootcert': 'rds-combined-ca-bundle.pem',
            'sslmode': 'verify-full'
        })

        # Test empty options
        os.environ['DATABASE_URL'] = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg'
                                      '@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?')
        url = parse_from_environment()['default']
        self.assertNotIn('OPTIONS', url)

    def test_mysql_database_url_with_sslca_options(self):
        os.environ['DATABASE_URL'] = 'mysql://uf07k1i6d8ia0v:wegauwhgeuioweg' \
                                     '@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn' \
                                     '?ssl-ca=rds-combined-ca-bundle.pem'
        url = parse_from_environment()['default']

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

        # Test empty options
        os.environ['DATABASE_URL'] = ('mysql://uf07k1i6d8ia0v:wegauwhgeuioweg'
                                      '@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn?')
        url = parse_from_environment()['default']
        self.assertNotIn('OPTIONS', url)

    def test_oracle_parsing(self):
        url = 'oracle://scott:tiger@oraclehost:1521/hr'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.oracle')
        self.assertEqual(url['NAME'], 'hr')
        self.assertEqual(url['HOST'], 'oraclehost')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['PORT'], 1521)

    def test_oracle_gis_parsing(self):
        url = 'oraclegis://scott:tiger@oraclehost:1521/hr'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.oracle')
        self.assertEqual(url['NAME'], 'hr')
        self.assertEqual(url['HOST'], 'oraclehost')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['PORT'], 1521)

    def test_oracle_dsn_parsing(self):
        url = (
            'oracle://scott:tiger@/'
            '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)'
            '(HOST=oraclehost)(PORT=1521)))'
            '(CONNECT_DATA=(SID=hr)))'
        )
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.oracle')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['HOST'], '')
        self.assertEqual(url['PORT'], '')

        dsn = (
            '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)'
            '(HOST=oraclehost)(PORT=1521)))'
            '(CONNECT_DATA=(SID=hr)))'
        )

        self.assertEqual(url['NAME'], dsn)

    def test_oracle_tns_parsing(self):
        url = 'oracle://scott:tiger@/tnsname'
        url = parse_url(url)

        self.assertEqual(url['ENGINE'], 'django.db.backends.oracle')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['NAME'], 'tnsname')
        self.assertEqual(url['HOST'], '')
        self.assertEqual(url['PORT'], '')

    def test_redshift_parsing(self):
        url = ('postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5439'
               '/d8r82722r2kuvn?currentSchema=otherschema')
        url = parse_url(url, ENGINE='django_redshift_backend')

        self.assertEqual(url['ENGINE'], 'django_redshift_backend')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5439)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])
