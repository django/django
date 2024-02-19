from __future__ import annotations

from typing import NoReturn

import attr
import pytest

from .._highlevel_generic import StapledStream
from ..abc import ReceiveStream, SendStream


@attr.s
class RecordSendStream(SendStream):
    record: list[str | tuple[str, object]] = attr.ib(factory=list)

    async def send_all(self, data: object) -> None:
        self.record.append(("send_all", data))

    async def wait_send_all_might_not_block(self) -> None:
        self.record.append("wait_send_all_might_not_block")

    async def aclose(self) -> None:
        self.record.append("aclose")


@attr.s
class RecordReceiveStream(ReceiveStream):
    record: list[str | tuple[str, int | None]] = attr.ib(factory=list)

    async def receive_some(self, max_bytes: int | None = None) -> bytes:
        self.record.append(("receive_some", max_bytes))
        return b""

    async def aclose(self) -> None:
        self.record.append("aclose")


async def test_StapledStream() -> None:
    send_stream = RecordSendStream()
    receive_stream = RecordReceiveStream()
    stapled = StapledStream(send_stream, receive_stream)

    assert stapled.send_stream is send_stream
    assert stapled.receive_stream is receive_stream

    await stapled.send_all(b"foo")
    await stapled.wait_send_all_might_not_block()
    assert send_stream.record == [
        ("send_all", b"foo"),
        "wait_send_all_might_not_block",
    ]
    send_stream.record.clear()

    await stapled.send_eof()
    assert send_stream.record == ["aclose"]
    send_stream.record.clear()

    async def fake_send_eof() -> None:
        send_stream.record.append("send_eof")

    send_stream.send_eof = fake_send_eof  # type: ignore[attr-defined]
    await stapled.send_eof()
    assert send_stream.record == ["send_eof"]

    send_stream.record.clear()
    assert receive_stream.record == []

    await stapled.receive_some(1234)
    assert receive_stream.record == [("receive_some", 1234)]
    assert send_stream.record == []
    receive_stream.record.clear()

    await stapled.aclose()
    assert receive_stream.record == ["aclose"]
    assert send_stream.record == ["aclose"]


async def test_StapledStream_with_erroring_close() -> None:
    # Make sure that if one of the aclose methods errors out, then the other
    # one still gets called.
    class BrokenSendStream(RecordSendStream):
        async def aclose(self) -> NoReturn:
            await super().aclose()
            raise ValueError("send error")

    class BrokenReceiveStream(RecordReceiveStream):
        async def aclose(self) -> NoReturn:
            await super().aclose()
            raise ValueError("recv error")

    stapled = StapledStream(BrokenSendStream(), BrokenReceiveStream())

    with pytest.raises(ValueError, match="^(send|recv) error$") as excinfo:
        await stapled.aclose()
    assert isinstance(excinfo.value.__context__, ValueError)

    assert stapled.send_stream.record == ["aclose"]
    assert stapled.receive_stream.record == ["aclose"]
