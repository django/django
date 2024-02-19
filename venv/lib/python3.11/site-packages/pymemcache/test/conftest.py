import os.path
import socket
import ssl

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--server", action="store", default="localhost", help="memcached server"
    )

    parser.addoption(
        "--port", action="store", default="11211", help="memcached server port"
    )

    parser.addoption(
        "--tls-server", action="store", default="localhost", help="TLS memcached server"
    )

    parser.addoption(
        "--tls-port", action="store", default="11212", help="TLS memcached server port"
    )

    parser.addoption(
        "--size", action="store", default=1024, help="size of data in benchmarks"
    )

    parser.addoption(
        "--count",
        action="store",
        default=10000,
        help="number of iterations to run each benchmark",
    )

    parser.addoption(
        "--keys",
        action="store",
        default=20,
        help="number of keys to use for multi benchmarks",
    )


@pytest.fixture(scope="session")
def host(request):
    return request.config.option.server


@pytest.fixture(scope="session")
def port(request):
    return int(request.config.option.port)


@pytest.fixture(scope="session")
def tls_host(request):
    return request.config.option.tls_server


@pytest.fixture(scope="session")
def tls_port(request):
    return int(request.config.option.tls_port)


@pytest.fixture(scope="session")
def size(request):
    return int(request.config.option.size)


@pytest.fixture(scope="session")
def count(request):
    return int(request.config.option.count)


@pytest.fixture(scope="session")
def keys(request):
    return int(request.config.option.keys)


@pytest.fixture(scope="session")
def pairs(size, keys):
    return {"pymemcache_test:%d" % i: "X" * size for i in range(keys)}


@pytest.fixture(scope="session")
def tls_context():
    return ssl.create_default_context(
        cafile=os.path.join(os.path.dirname(__file__), "certs/ca-root.crt")
    )


def pytest_generate_tests(metafunc):
    if "socket_module" in metafunc.fixturenames:
        socket_modules = [socket]
        try:
            from gevent import socket as gevent_socket  # type: ignore
        except ImportError:
            print("Skipping gevent (not installed)")
        else:
            socket_modules.append(gevent_socket)

        metafunc.parametrize("socket_module", socket_modules)

    if "client_class" in metafunc.fixturenames:
        from pymemcache.client.base import Client, PooledClient
        from pymemcache.client.hash import HashClient

        class HashClientSingle(HashClient):
            def __init__(self, server, *args, **kwargs):
                super().__init__([server], *args, **kwargs)

        metafunc.parametrize("client_class", [Client, PooledClient, HashClientSingle])

    if "key_prefix" in metafunc.fixturenames:
        mark = metafunc.definition.get_closest_marker("parametrize")
        if not mark or "key_prefix" not in mark.args[0]:
            metafunc.parametrize("key_prefix", [b"", b"prefix"])
