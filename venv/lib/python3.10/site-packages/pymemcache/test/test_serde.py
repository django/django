from unittest import TestCase

from pymemcache.serde import (
    CompressedSerde,
    pickle_serde,
    PickleSerde,
    FLAG_BYTES,
    FLAG_COMPRESSED,
    FLAG_PICKLE,
    FLAG_INTEGER,
    FLAG_TEXT,
)
import pytest
import pickle
import sys
import zlib


class CustomInt(int):
    """
    Custom integer type for testing.

    Entirely useless, but used to show that built in types get serialized and
    deserialized back as the same type of object.
    """

    pass


def check(serde, value, expected_flags):
    serialized, flags = serde.serialize(b"key", value)
    assert flags == expected_flags

    # pymemcache stores values as byte strings, so we immediately the value
    # if needed so deserialized works as it would with a real server
    if not isinstance(serialized, bytes):
        serialized = str(serialized).encode("ascii")

    deserialized = serde.deserialize(b"key", serialized, flags)
    assert deserialized == value


@pytest.mark.unit()
class TestSerde:
    serde = pickle_serde

    def test_bytes(self):
        check(self.serde, b"value", FLAG_BYTES)
        check(self.serde, b"\xc2\xa3 $ \xe2\x82\xac", FLAG_BYTES)  # £ $ €

    def test_unicode(self):
        check(self.serde, "value", FLAG_TEXT)
        check(self.serde, "£ $ €", FLAG_TEXT)

    def test_int(self):
        check(self.serde, 1, FLAG_INTEGER)

    def test_pickleable(self):
        check(self.serde, {"a": "dict"}, FLAG_PICKLE)

    def test_subtype(self):
        # Subclass of a native type will be restored as the same type
        check(self.serde, CustomInt(123123), FLAG_PICKLE)


@pytest.mark.unit()
class TestSerdePickleVersion0(TestCase):
    serde = PickleSerde(pickle_version=0)


@pytest.mark.unit()
class TestSerdePickleVersion1(TestCase):
    serde = PickleSerde(pickle_version=1)


@pytest.mark.unit()
class TestSerdePickleVersion2(TestCase):
    serde = PickleSerde(pickle_version=2)


@pytest.mark.unit()
class TestSerdePickleVersionHighest(TestCase):
    serde = PickleSerde(pickle_version=pickle.HIGHEST_PROTOCOL)


@pytest.mark.parametrize("serde", [pickle_serde, CompressedSerde()])
@pytest.mark.unit()
def test_compressed_simple(serde):
    # test_bytes
    check(serde, b"value", FLAG_BYTES)
    check(serde, b"\xc2\xa3 $ \xe2\x82\xac", FLAG_BYTES)  # £ $ €

    # test_unicode
    check(serde, "value", FLAG_TEXT)
    check(serde, "£ $ €", FLAG_TEXT)

    # test_int
    check(serde, 1, FLAG_INTEGER)

    # test_pickleable
    check(serde, {"a": "dict"}, FLAG_PICKLE)

    # test_subtype
    # Subclass of a native type will be restored as the same type
    check(serde, CustomInt(12312), FLAG_PICKLE)


@pytest.mark.parametrize(
    "serde",
    [
        CompressedSerde(min_compress_len=49),
        # Custom compression.  This could be something like lz4
        CompressedSerde(
            compress=lambda value: zlib.compress(value, 9),
            decompress=lambda value: zlib.decompress(value),
            min_compress_len=49,
        ),
    ],
)
@pytest.mark.unit()
def test_compressed_complex(serde):
    # test_bytes
    check(serde, b"value" * 10, FLAG_BYTES | FLAG_COMPRESSED)
    check(serde, b"\xc2\xa3 $ \xe2\x82\xac" * 10, FLAG_BYTES | FLAG_COMPRESSED)  # £ $ €

    # test_unicode
    check(serde, "value" * 10, FLAG_TEXT | FLAG_COMPRESSED)
    check(serde, "£ $ €" * 10, FLAG_TEXT | FLAG_COMPRESSED)

    # test_int, doesn't make sense to compress
    check(serde, sys.maxsize, FLAG_INTEGER)

    # test_pickleable
    check(
        serde,
        {
            "foo": "bar",
            "baz": "qux",
            "uno": "dos",
            "tres": "tres",
        },
        FLAG_PICKLE | FLAG_COMPRESSED,
    )

    # test_subtype
    # Subclass of a native type will be restored as the same type
    check(serde, CustomInt(sys.maxsize), FLAG_PICKLE | FLAG_COMPRESSED)
