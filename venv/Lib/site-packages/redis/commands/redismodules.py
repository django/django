from __future__ import annotations

from json import JSONDecoder, JSONEncoder
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bf import BFBloom, CFBloom, CMSBloom, TDigestBloom, TOPKBloom
    from .json import JSON
    from .search import AsyncSearch, Search
    from .timeseries import TimeSeries
    from .vectorset import VectorSet


class RedisModuleCommands:
    """This class contains the wrapper functions to bring supported redis
    modules into the command namespace.
    """

    def json(self, encoder=JSONEncoder(), decoder=JSONDecoder()) -> JSON:
        """Access the json namespace, providing support for redis json."""

        from .json import JSON

        jj = JSON(client=self, encoder=encoder, decoder=decoder)
        return jj

    def ft(self, index_name="idx") -> Search:
        """Access the search namespace, providing support for redis search."""

        from .search import Search

        s = Search(client=self, index_name=index_name)
        return s

    def ts(self) -> TimeSeries:
        """Access the timeseries namespace, providing support for
        redis timeseries data.
        """

        from .timeseries import TimeSeries

        s = TimeSeries(client=self)
        return s

    def bf(self) -> BFBloom:
        """Access the bloom namespace."""

        from .bf import BFBloom

        bf = BFBloom(client=self)
        return bf

    def cf(self) -> CFBloom:
        """Access the bloom namespace."""

        from .bf import CFBloom

        cf = CFBloom(client=self)
        return cf

    def cms(self) -> CMSBloom:
        """Access the bloom namespace."""

        from .bf import CMSBloom

        cms = CMSBloom(client=self)
        return cms

    def topk(self) -> TOPKBloom:
        """Access the bloom namespace."""

        from .bf import TOPKBloom

        topk = TOPKBloom(client=self)
        return topk

    def tdigest(self) -> TDigestBloom:
        """Access the bloom namespace."""

        from .bf import TDigestBloom

        tdigest = TDigestBloom(client=self)
        return tdigest

    def vset(self) -> VectorSet:
        """Access the VectorSet commands namespace."""

        from .vectorset import VectorSet

        vset = VectorSet(client=self)
        return vset


class AsyncRedisModuleCommands(RedisModuleCommands):
    def ft(self, index_name="idx") -> AsyncSearch:
        """Access the search namespace, providing support for redis search."""

        from .search import AsyncSearch

        s = AsyncSearch(client=self, index_name=index_name)
        return s
