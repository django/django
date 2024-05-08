from pymemcache.client.rendezvous import RendezvousHash
import pytest


@pytest.mark.unit()
def test_init_no_options():
    rendezvous = RendezvousHash()
    assert 0 == len(rendezvous.nodes)
    assert 1361238019 == rendezvous.hash_function("6666")


@pytest.mark.unit()
def test_init():
    nodes = ["0", "1", "2"]
    rendezvous = RendezvousHash(nodes=nodes)
    assert 3 == len(rendezvous.nodes)
    assert 1361238019 == rendezvous.hash_function("6666")


@pytest.mark.unit()
def test_seed():
    rendezvous = RendezvousHash(seed=10)
    assert 2981722772 == rendezvous.hash_function("6666")


@pytest.mark.unit()
def test_add_node():
    rendezvous = RendezvousHash()
    rendezvous.add_node("1")

    assert 1 == len(rendezvous.nodes)
    rendezvous.add_node("1")

    assert 1 == len(rendezvous.nodes)
    rendezvous.add_node("2")

    assert 2 == len(rendezvous.nodes)
    rendezvous.add_node("1")

    assert 2 == len(rendezvous.nodes)


@pytest.mark.unit()
def test_remove_node():
    nodes = ["0", "1", "2"]
    rendezvous = RendezvousHash(nodes=nodes)
    rendezvous.remove_node("2")

    assert 2 == len(rendezvous.nodes)

    with pytest.raises(ValueError):
        rendezvous.remove_node("2")

    assert 2 == len(rendezvous.nodes)

    rendezvous.remove_node("1")
    assert 1 == len(rendezvous.nodes)

    rendezvous.remove_node("0")
    assert 0 == len(rendezvous.nodes)


@pytest.mark.unit()
def test_get_node():
    nodes = ["0", "1", "2"]
    rendezvous = RendezvousHash(nodes=nodes)
    assert "0" == rendezvous.get_node("ok")
    assert "1" == rendezvous.get_node("mykey")
    assert "2" == rendezvous.get_node("wat")


@pytest.mark.unit()
def test_get_node_after_removal():
    nodes = ["0", "1", "2"]
    rendezvous = RendezvousHash(nodes=nodes)
    rendezvous.remove_node("1")

    assert "0" == rendezvous.get_node("ok")
    assert "0" == rendezvous.get_node("mykey")
    assert "2" == rendezvous.get_node("wat")


@pytest.mark.unit()
def test_get_node_after_addition():
    nodes = ["0", "1", "2"]
    rendezvous = RendezvousHash(nodes=nodes)
    assert "0" == rendezvous.get_node("ok")
    assert "1" == rendezvous.get_node("mykey")
    assert "2" == rendezvous.get_node("wat")
    assert "2" == rendezvous.get_node("lol")
    rendezvous.add_node("3")

    assert "0" == rendezvous.get_node("ok")
    assert "1" == rendezvous.get_node("mykey")
    assert "2" == rendezvous.get_node("wat")
    assert "3" == rendezvous.get_node("lol")


@pytest.mark.unit()
def test_grow():
    rendezvous = RendezvousHash()

    placements = {}

    for i in range(10):
        rendezvous.add_node(str(i))
        placements[str(i)] = []

    for i in range(1000):
        node = rendezvous.get_node(str(i))
        placements[node].append(i)

    new_placements = {}

    for i in range(20):
        rendezvous.add_node(str(i))
        new_placements[str(i)] = []

    for i in range(1000):
        node = rendezvous.get_node(str(i))
        new_placements[node].append(i)

    keys = [k for sublist in placements.values() for k in sublist]
    new_keys = [k for sublist in new_placements.values() for k in sublist]
    assert sorted(keys) == sorted(new_keys)

    added = 0
    removed = 0

    for node, assignments in new_placements.items():
        after = set(assignments)
        before = set(placements.get(node, []))
        removed += len(before.difference(after))
        added += len(after.difference(before))

    assert added == removed
    assert 1062 == (added + removed)


@pytest.mark.unit()
def test_shrink():
    rendezvous = RendezvousHash()

    placements = {}
    for i in range(10):
        rendezvous.add_node(str(i))
        placements[str(i)] = []

    for i in range(1000):
        node = rendezvous.get_node(str(i))
        placements[node].append(i)

    rendezvous.remove_node("9")
    new_placements = {}
    for i in range(9):
        new_placements[str(i)] = []

    for i in range(1000):
        node = rendezvous.get_node(str(i))
        new_placements[node].append(i)

    keys = [k for sublist in placements.values() for k in sublist]
    new_keys = [k for sublist in new_placements.values() for k in sublist]
    assert sorted(keys) == sorted(new_keys)

    added = 0
    removed = 0
    for node, assignments in placements.items():
        after = set(assignments)
        before = set(new_placements.get(node, []))
        removed += len(before.difference(after))
        added += len(after.difference(before))

    assert added == removed
    assert 202 == (added + removed)


def collide(key, seed):
    return 1337


@pytest.mark.unit()
def test_rendezvous_collision():
    nodes = ["c", "b", "a"]
    rendezvous = RendezvousHash(nodes, hash_function=collide)

    for i in range(1000):
        assert "c" == rendezvous.get_node(i)


@pytest.mark.unit()
def test_rendezvous_names():
    nodes = [1, 2, 3, "a", "b", "lol.wat.com"]
    rendezvous = RendezvousHash(nodes, hash_function=collide)

    for i in range(10):
        assert "lol.wat.com" == rendezvous.get_node(i)

    nodes = [1, "a", "0"]
    rendezvous = RendezvousHash(nodes, hash_function=collide)

    for i in range(10):
        assert "a" == rendezvous.get_node(i)
