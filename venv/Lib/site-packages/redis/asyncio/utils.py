from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio.client import Pipeline, Redis


def from_url(url: str, **kwargs: Any) -> "Redis":
    """
    Returns an active Redis client generated from the given database URL.

    Will attempt to extract the database id from the path url fragment, if
    none is provided.
    """
    from redis.asyncio.client import Redis

    return Redis.from_url(url, **kwargs)


class pipeline:  # noqa: N801
    def __init__(self, redis_obj: "Redis"):
        self.p: "Pipeline" = redis_obj.pipeline()

    async def __aenter__(self) -> "Pipeline":
        return self.p

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.p.execute()
        del self.p
