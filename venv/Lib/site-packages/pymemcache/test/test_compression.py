from pymemcache.client.base import Client
from pymemcache.serde import (
    CompressedSerde,
    pickle_serde,
)

from faker import Faker

import pytest
import random
import string
import time
import zstd  # type: ignore
import zlib

fake = Faker(["it_IT", "en_US", "ja_JP"])


def get_random_string(length):
    letters = string.ascii_letters
    chars = string.punctuation
    digits = string.digits
    total = letters + chars + digits
    result_str = "".join(random.choice(total) for i in range(length))
    return result_str


class CustomObject:
    """
    Custom class for verifying serialization
    """

    def __init__(self):
        self.number = random.randint(0, 100)
        self.string = fake.text()
        self.object = fake.profile()


class CustomObjectValue:
    def __init__(self, value):
        self.value = value


def benchmark(count, func, *args, **kwargs):
    start = time.time()

    for _ in range(count):
        result = func(*args, **kwargs)

    duration = time.time() - start
    print(str(duration))

    return result


@pytest.fixture(scope="session")
def names():
    names = []
    for _ in range(15):
        names.append(fake.name())

    return names


@pytest.fixture(scope="session")
def paragraphs():
    paragraphs = []
    for _ in range(15):
        paragraphs.append(fake.text())

    return paragraphs


@pytest.fixture(scope="session")
def objects():
    objects = []
    for _ in range(15):
        objects.append(CustomObject())

    return objects


# Always run compression for the benchmarks
min_compress_len = 1

default_serde = CompressedSerde(min_compress_len=min_compress_len)

zlib_serde = CompressedSerde(
    compress=lambda value: zlib.compress(value, 9),
    decompress=lambda value: zlib.decompress(value),
    min_compress_len=min_compress_len,
)

zstd_serde = CompressedSerde(
    compress=lambda value: zstd.compress(value),
    decompress=lambda value: zstd.decompress(value),
    min_compress_len=min_compress_len,
)

serializers = [
    None,
    default_serde,
    zlib_serde,
    zstd_serde,
]
ids = ["none", "zlib ", "zlib9", "zstd "]


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_set_strings(count, host, port, serde, names):
    client = Client((host, port), serde=serde, encoding="utf-8")

    def test():
        for index, name in enumerate(names):
            key = f"name_{index}"
            client.set(key, name)

    benchmark(count, test)


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_get_strings(count, host, port, serde, names):
    client = Client((host, port), serde=serde, encoding="utf-8")
    for index, name in enumerate(names):
        key = f"name_{index}"
        client.set(key, name)

    def test():
        for index, _ in enumerate(names):
            key = f"name_{index}"
            client.get(key)

    benchmark(count, test)


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_set_large_strings(count, host, port, serde, paragraphs):
    client = Client((host, port), serde=serde, encoding="utf-8")

    def test():
        for index, p in enumerate(paragraphs):
            key = f"paragraph_{index}"
            client.set(key, p)

    benchmark(count, test)


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_get_large_strings(count, host, port, serde, paragraphs):
    client = Client((host, port), serde=serde, encoding="utf-8")
    for index, p in enumerate(paragraphs):
        key = f"paragraphs_{index}"
        client.set(key, p)

    def test():
        for index, _ in enumerate(paragraphs):
            key = f"paragraphs_{index}"
            client.get(key)

    benchmark(count, test)


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_set_objects(count, host, port, serde, objects):
    client = Client((host, port), serde=serde, encoding="utf-8")

    def test():
        for index, o in enumerate(objects):
            key = f"objects_{index}"
            client.set(key, o)

    benchmark(count, test)


@pytest.mark.benchmark()
@pytest.mark.parametrize("serde", serializers, ids=ids)
def test_bench_compress_get_objects(count, host, port, serde, objects):
    client = Client((host, port), serde=serde, encoding="utf-8")
    for index, o in enumerate(objects):
        key = f"objects_{index}"
        client.set(key, o)

    def test():
        for index, _ in enumerate(objects):
            key = f"objects_{index}"
            client.get(key)

    benchmark(count, test)


@pytest.mark.benchmark()
def test_optimal_compression_length():
    for length in range(5, 2000):
        input_data = get_random_string(length)
        start = len(input_data)

        for index, serializer in enumerate(serializers[1:]):
            name = ids[index + 1]
            value, _ = serializer.serialize("foo", input_data)
            end = len(value)
            print(f"serializer={name}\t start={start}\t end={end}")


@pytest.mark.benchmark()
def test_optimal_compression_length_objects():
    for length in range(5, 2000):
        input_data = get_random_string(length)
        obj = CustomObjectValue(input_data)
        start = len(pickle_serde.serialize("foo", obj)[0])

        for index, serializer in enumerate(serializers[1:]):
            name = ids[index + 1]
            value, _ = serializer.serialize("foo", obj)
            end = len(value)
            print(f"serializer={name}\t start={start}\t end={end}")
