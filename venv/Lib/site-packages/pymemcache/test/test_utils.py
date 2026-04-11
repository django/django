import pytest

from pymemcache.test.utils import MockMemcacheClient


@pytest.mark.unit()
def test_get_set():
    client = MockMemcacheClient()
    assert client.get(b"hello") is None

    client.set(b"hello", 12)
    assert client.get(b"hello") == 12


@pytest.mark.unit()
def test_get_set_unicide_key():
    client = MockMemcacheClient()
    assert client.get("hello") is None

    client.set(b"hello", 12)
    assert client.get("hello") == 12


@pytest.mark.unit()
def test_get_set_non_ascii_value():
    client = MockMemcacheClient()
    assert client.get(b"hello") is None

    # This is the value of msgpack.packb('non_ascii')
    non_ascii_str = b"\xa9non_ascii"
    client.set(b"hello", non_ascii_str)
    assert client.get(b"hello") == non_ascii_str


@pytest.mark.unit()
def test_get_many_set_many():
    client = MockMemcacheClient()
    client.set(b"h", 1)

    result = client.get_many([b"h", b"e", b"l", b"o"])
    assert result == {b"h": 1}

    # Convert keys into bytes
    d = {k.encode("ascii"): v for k, v in dict(h=1, e=2, z=3).items()}
    client.set_many(d)
    assert client.get_many([b"h", b"e", b"z", b"o"]) == d


@pytest.mark.unit()
def test_get_many_set_many_non_ascii_values():
    client = MockMemcacheClient()

    # These are the values of calling msgpack.packb() on '1', '2', and '3'
    non_ascii_1 = b"\xa11"
    non_ascii_2 = b"\xa12"
    non_ascii_3 = b"\xa13"
    client.set(b"h", non_ascii_1)

    result = client.get_many([b"h", b"e", b"l", b"o"])
    assert result == {b"h": non_ascii_1}

    # Convert keys into bytes
    d = {
        k.encode("ascii"): v
        for k, v in dict(h=non_ascii_1, e=non_ascii_2, z=non_ascii_3).items()
    }
    client.set_many(d)
    assert client.get_many([b"h", b"e", b"z", b"o"]) == d


@pytest.mark.unit()
def test_add():
    client = MockMemcacheClient()

    client.add(b"k", 2)
    assert client.get(b"k") == 2

    client.add(b"k", 25)
    assert client.get(b"k") == 2


@pytest.mark.unit()
def test_delete():
    client = MockMemcacheClient()

    client.add(b"k", 2)
    assert client.get(b"k") == 2

    client.delete(b"k")
    assert client.get(b"k") is None


@pytest.mark.unit()
def test_incr_decr():
    client = MockMemcacheClient()

    client.add(b"k", 2)

    client.incr(b"k", 4)
    assert client.get(b"k") == 6

    client.decr(b"k", 2)
    assert client.get(b"k") == 4


@pytest.mark.unit()
def test_prepand_append():
    client = MockMemcacheClient()

    client.set(b"k", "1")
    client.append(b"k", "a")
    client.prepend(b"k", "p")
    assert client.get(b"k") == b"p1a"
