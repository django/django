# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import pytest

try:
    import pylibmc  # type: ignore

    HAS_PYLIBMC = True
except Exception:
    HAS_PYLIBMC = False

try:
    import memcache  # type: ignore

    HAS_MEMCACHE = True
except Exception:
    HAS_MEMCACHE = False


try:
    import pymemcache.client

    HAS_PYMEMCACHE = True
except Exception:
    HAS_PYMEMCACHE = False


@pytest.fixture(
    params=[
        "pylibmc",
        "memcache",
        "pymemcache",
    ]
)
def client(request, host, port):
    if request.param == "pylibmc":
        if not HAS_PYLIBMC:
            pytest.skip("requires pylibmc")
        client = pylibmc.Client([f"{host}:{port}"])
        client.behaviors = {"tcp_nodelay": True}

    elif request.param == "memcache":
        if not HAS_MEMCACHE:
            pytest.skip("requires python-memcached")
        client = memcache.Client([f"{host}:{port}"])

    elif request.param == "pymemcache":
        if not HAS_PYMEMCACHE:
            pytest.skip("requires pymemcache")
        client = pymemcache.client.Client((host, port))

    else:
        pytest.skip(f"unknown library {request.param}")

    client.flush_all()
    return client


def benchmark(count, func, *args, **kwargs):
    start = time.time()

    for _ in range(count):
        result = func(*args, **kwargs)

    duration = time.time() - start
    print(str(duration))

    return result


@pytest.mark.benchmark()
def test_bench_get(request, client, pairs, count):
    key = "pymemcache_test:0"
    value = pairs[key]
    client.set(key, value)
    benchmark(count, client.get, key)


@pytest.mark.benchmark()
def test_bench_set(request, client, pairs, count):
    key = "pymemcache_test:0"
    value = pairs[key]
    benchmark(count, client.set, key, value)


@pytest.mark.benchmark()
def test_bench_get_multi(request, client, pairs, count):
    client.set_multi(pairs)
    benchmark(count, client.get_multi, list(pairs))


@pytest.mark.benchmark()
def test_bench_set_multi(request, client, pairs, count):
    benchmark(count, client.set_multi, pairs)


@pytest.mark.benchmark()
def test_bench_delete(request, client, pairs, count):
    benchmark(count, client.delete, next(pairs))


@pytest.mark.benchmark()
def test_bench_delete_multi(request, client, pairs, count):
    # deleting missing key takes the same work client-side as real keys
    benchmark(count, client.delete_multi, list(pairs.keys()))
