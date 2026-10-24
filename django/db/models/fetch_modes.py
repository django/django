from django.core.exceptions import FieldFetchBlocked, SynchronousOnlyOperation

ASYNC_UNSAFE_FETCH_MSG = (
    "Fetching of {model}.{field} would require a database query, which cannot "
    "be done from an async context. Use select_related() or "
    "prefetch_related() to fetch it in advance, or use sync_to_async()."
)


class FetchMode:
    __slots__ = ()

    track_peers = False

    def fetch(self, fetcher, instance):
        raise NotImplementedError("Subclasses must implement this method.")

    def _raise_async_unsafe(self, fetcher, instance, exc):
        raise SynchronousOnlyOperation(
            ASYNC_UNSAFE_FETCH_MSG.format(
                model=instance.__class__.__qualname__,
                field=fetcher.field.name,
            )
        ) from exc


class FetchOne(FetchMode):
    __slots__ = ()

    def fetch(self, fetcher, instance):
        try:
            fetcher.fetch_one(instance)
        except SynchronousOnlyOperation as exc:
            self._raise_async_unsafe(fetcher, instance, exc)

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
        try:
            if len(instances) > 1:
                fetcher.fetch_many(instances)
            else:
                fetcher.fetch_one(instance)
        except SynchronousOnlyOperation as exc:
            self._raise_async_unsafe(fetcher, instance, exc)

    def __reduce__(self):
        return "FETCH_PEERS"


FETCH_PEERS = FetchPeers()


class FetchRaise(FetchMode):
    __slots__ = ()

    def fetch(self, fetcher, instance):
        klass = instance.__class__.__qualname__
        field_name = fetcher.field.name
        raise FieldFetchBlocked(f"Fetching of {klass}.{field_name} blocked.") from None

    def __reduce__(self):
        return "FETCH_RAISE"


FETCH_RAISE = FetchRaise()
