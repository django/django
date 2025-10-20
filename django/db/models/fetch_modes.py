from django.core.exceptions import FieldFetchBlocked


class FetchMode:
    __slots__ = ()

    track_peers = False

    def fetch(self, fetcher, instance):
        raise NotImplementedError("Subclasses must implement this method.")


class FetchOne(FetchMode):
    __slots__ = ()

    def fetch(self, fetcher, instance):
        fetcher.fetch_one(instance)

    def __reduce__(self):
        return "FETCH_ONE"


FETCH_ONE = FetchOne()


class FetchPeers(FetchMode):
    __slots__ = ()

    track_peers = True

    def fetch(self, fetcher, instance):
        instances = [
            peer
            for peer_weakref in instance._state.peers
            if (peer := peer_weakref()) is not None
        ]
        if len(instances) > 1:
            fetcher.fetch_many(instances)
        else:
            fetcher.fetch_one(instance)

    def __reduce__(self):
        return "FETCH_PEERS"


FETCH_PEERS = FetchPeers()


class Raise(FetchMode):
    __slots__ = ()

    def fetch(self, fetcher, instance):
        klass = instance.__class__.__qualname__
        field_name = fetcher.field.name
        raise FieldFetchBlocked(f"Fetching of {klass}.{field_name} blocked.") from None

    def __reduce__(self):
        return "RAISE"


RAISE = Raise()
