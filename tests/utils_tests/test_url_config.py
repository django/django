# -*- coding: utf-8 -*-
# !/usr/bin/env python
import unittest

from django.conf.service_url import configure_cache, configure_db, parse_url
from django.db import connection

GENERIC_TESTS = [
    (
        "username:password@domain/database",
        ("username", "password", "domain", "", "database", {}),
    ),
    (
        "username:password@domain:123/database",
        ("username", "password", "domain", 123, "database", {}),
    ),
    ("domain:123/database", ("", "", "domain", 123, "database", {})),
    ("user@domain:123/database", ("user", "", "domain", 123, "database", {})),
    (
        "username:password@[2001:db8:1234::1234:5678:90af]:123/database",
        ("username", "password", "2001:db8:1234::1234:5678:90af", 123, "database", {}),
    ),
    (
        "username:password@host:123/database?reconnect=true",
        ("username", "password", "host", 123, "database", {"reconnect": True}),
    ),
    ("username:password@/database", ("username", "password", "", "", "database", {})),
]


class BaseURLTests:
    SCHEME = None
    STRING_PORTS = False  # Workaround for Oracle

    def test_parsing(self):
        for value, (user, passw, host, port, database, options) in GENERIC_TESTS:
            value = "{scheme}://{value}".format(scheme=self.SCHEME, value=value)

            with self.subTest(value=value):
                result = configure_db(value)
                self.assertEqual(result["NAME"], database)
                self.assertEqual(result["HOST"], host)
                self.assertEqual(result["USER"], user)
                self.assertEqual(result["PASSWORD"], passw)
                self.assertEqual(
                    result["PORT"], port if not self.STRING_PORTS else str(port)
                )
                self.assertDictEqual(result["OPTIONS"], options)


@unittest.skipUnless(connection.vendor == "sqlite", "Sqlite tests")
class SqliteTests(BaseURLTests, unittest.TestCase):
    SCHEME = "sqlite"

    def test_empty_url(self):
        url = "sqlite://"
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(url["NAME"], ":memory:")

    def test_memory_url(self):
        url = "sqlite://:memory:"
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(url["NAME"], ":memory:")


@unittest.skipUnless(connection.vendor == "postgresql", "Postgres tests")
class PostgresTests(BaseURLTests, unittest.TestCase):
    SCHEME = "postgres"

    def test_unix_socket_parsing(self):
        url = "postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn"
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url["NAME"], "d8r82722r2kuvn")
        self.assertEqual(url["HOST"], "/var/run/postgresql")
        self.assertEqual(url["USER"], "")
        self.assertEqual(url["PASSWORD"], "")
        self.assertEqual(url["PORT"], "")

        url = "postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn"
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url["HOST"], "/Users/postgres/RuN")
        self.assertEqual(url["USER"], "")
        self.assertEqual(url["PASSWORD"], "")
        self.assertEqual(url["PORT"], "")

    def test_search_path_parsing(self):
        url = (
            "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431"
            "/d8r82722r2kuvn?currentSchema=otherschema"
        )
        url = configure_db(url)
        self.assertEqual(url["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url["NAME"], "d8r82722r2kuvn")
        self.assertEqual(url["HOST"], "ec2-107-21-253-135.compute-1.amazonaws.com")
        self.assertEqual(url["USER"], "uf07k1i6d8ia0v")
        self.assertEqual(url["PASSWORD"], "wegauwhgeuioweg")
        self.assertEqual(url["PORT"], 5431)
        self.assertEqual(url["OPTIONS"]["options"], "-c search_path=otherschema")
        self.assertNotIn("currentSchema", url["OPTIONS"])

    def test_parsing_with_special_characters(self):
        url = "postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database"
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url["NAME"], "#database")
        self.assertEqual(url["HOST"], "ec2-107-21-253-135.compute-1.amazonaws.com")
        self.assertEqual(url["USER"], "#user")
        self.assertEqual(url["PASSWORD"], "#password")
        self.assertEqual(url["PORT"], 5431)

    def test_database_url_with_options(self):
        # Test full options
        url = (
            "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg"
            "@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
            "?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full"
        )
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url["NAME"], "d8r82722r2kuvn")
        self.assertEqual(url["HOST"], "ec2-107-21-253-135.compute-1.amazonaws.com")
        self.assertEqual(url["USER"], "uf07k1i6d8ia0v")
        self.assertEqual(url["PASSWORD"], "wegauwhgeuioweg")
        self.assertEqual(url["PORT"], 5431)
        self.assertEqual(
            url["OPTIONS"],
            {"sslrootcert": "rds-combined-ca-bundle.pem", "sslmode": "verify-full"},
        )

    def test_gis_search_path_parsing(self):
        url = (
            "postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431"
            "/d8r82722r2kuvn?currentSchema=otherschema"
        )
        url = configure_db(url)
        self.assertEqual(url["ENGINE"], "django.contrib.gis.db.backends.postgis")
        self.assertEqual(url["NAME"], "d8r82722r2kuvn")
        self.assertEqual(url["HOST"], "ec2-107-21-253-135.compute-1.amazonaws.com")
        self.assertEqual(url["USER"], "uf07k1i6d8ia0v")
        self.assertEqual(url["PASSWORD"], "wegauwhgeuioweg")
        self.assertEqual(url["PORT"], 5431)
        self.assertEqual(url["OPTIONS"]["options"], "-c search_path=otherschema")
        self.assertNotIn("currentSchema", url["OPTIONS"])


@unittest.skipUnless(connection.vendor == "mysql", "Mysql tests")
class MysqlTests(BaseURLTests, unittest.TestCase):
    SCHEME = "mysql"

    def test_with_sslca_options(self):
        url = (
            "mysql://uf07k1i6d8ia0v:wegauwhgeuioweg"
            "@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn"
            "?ssl-ca=rds-combined-ca-bundle.pem"
        )
        url = configure_db(url)

        self.assertEqual(url["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(url["NAME"], "d8r82722r2kuvn")
        self.assertEqual(url["HOST"], "ec2-107-21-253-135.compute-1.amazonaws.com")
        self.assertEqual(url["USER"], "uf07k1i6d8ia0v")
        self.assertEqual(url["PASSWORD"], "wegauwhgeuioweg")
        self.assertEqual(url["PORT"], 3306)
        self.assertEqual(url["OPTIONS"], {"ssl": {"ca": "rds-combined-ca-bundle.pem"}})


@unittest.skipUnless(connection.vendor == "oracle", "Oracle Tests")
class OracleTests(BaseURLTests, unittest.TestCase):
    SCHEME = "oracle"
    STRING_PORTS = True

    def test_dsn_parsing(self):
        dsn = (
            "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)"
            "(HOST=oraclehost)(PORT=1521)))"
            "(CONNECT_DATA=(SID=hr)))"
        )

        url = configure_db("oracle://scott:tiger@/" + dsn)

        self.assertEqual(url["ENGINE"], "django.db.backends.oracle")
        self.assertEqual(url["USER"], "scott")
        self.assertEqual(url["PASSWORD"], "tiger")
        self.assertEqual(url["HOST"], "")
        self.assertEqual(url["PORT"], "")

        url = configure_db(dsn)

        self.assertEqual(url["NAME"], dsn)


class TestCaches(unittest.TestCase):
    def test_local_caching_no_params(self):
        result = configure_cache("memory://")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.locmem.LocMemCache"
        )
        self.assertNotIn("LOCATION", result)

    def test_local_caching_with_location(self):
        result = configure_cache("memory://abc")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.locmem.LocMemCache"
        )
        self.assertEqual(result["LOCATION"], "abc")

    def test_database_caching(self):
        result = configure_cache("db://table-name")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.db.DatabaseCache"
        )
        self.assertEqual(result["LOCATION"], "table-name")

    def test_dummy_caching_no_params(self):
        result = configure_cache("dummy://")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.dummy.DummyCache"
        )
        self.assertNotIn("LOCATION", result)

    def test_dummy_caching_with_location(self):
        result = configure_cache("dummy://abc")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.dummy.DummyCache"
        )
        self.assertEqual(result["LOCATION"], "abc")

    def test_memcached_with_ip(self):
        result = configure_cache("memcached+pymemcache://1.2.3.4:1567")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.memcached.PyMemcacheCache"
        )
        self.assertEqual(result["LOCATION"], "1.2.3.4:1567")

    def test_memcached_without_port(self):
        result = configure_cache("memcached+pylibmccache://1.2.3.4")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache"
        )
        self.assertEqual(result["LOCATION"], "1.2.3.4")

    def test_memcached_socket_path(self):
        result = configure_cache("memcached+pymemcache:///tmp/memcached.sock")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.memcached.PyMemcacheCache"
        )
        self.assertEqual(result["LOCATION"], "/tmp/memcached.sock")

    def test_pylibmccache_memcached_unix_socket(self):
        result = configure_cache("memcached+pylibmccache://unix:/tmp/memcached.sock")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache"
        )
        self.assertEqual(result["LOCATION"], "unix:/tmp/memcached.sock")

    def test_file_cache_windows_path(self):
        result = configure_cache("file://C:/abc/def/xyz")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.filebased.FileBasedCache"
        )
        self.assertEqual(result["LOCATION"], "C:/abc/def/xyz")

    def test_file_cache_unix_path(self):
        result = configure_cache("file:///abc/def/xyz")
        self.assertEqual(
            result["BACKEND"], "django.core.cache.backends.filebased.FileBasedCache"
        )
        self.assertEqual(result["LOCATION"], "/abc/def/xyz")


class TestParseURL(unittest.TestCase):
    def test_hostname_sensitivity(self):
        parsed = parse_url("http://CaseSensitive")
        self.assertEqual(parsed["hostname"], "CaseSensitive")

    def test_port_is_an_integer(self):
        parsed = parse_url("http://CaseSensitive:123")
        self.assertIsInstance(parsed["port"], int)

    def test_path_strips_leading_slash(self):
        parsed = parse_url("http://test/abc")
        self.assertEqual(parsed["path"], "abc")

    def test_query_parameters_integer(self):
        parsed = parse_url("http://test/?a=1")
        self.assertDictEqual(parsed["options"], {"a": 1})

    def test_query_parameters_boolean(self):
        parsed = parse_url("http://test/?a=true&b=false")
        self.assertDictEqual(parsed["options"], {"a": True, "b": False})

    def test_query_last_parameter(self):
        parsed = parse_url("http://test/?a=one&a=two")
        self.assertDictEqual(parsed["options"], {"a": "two"})

    def test_does_not_reparse(self):
        parsed = parse_url("http://test/abc")
        self.assertIs(parse_url(parsed), parsed)
