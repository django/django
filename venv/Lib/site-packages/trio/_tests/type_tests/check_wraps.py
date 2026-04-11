# https://github.com/python-trio/trio/issues/2775#issuecomment-1702267589
# (except platform independent...)
import trio
from typing_extensions import assert_type


async def fn(s: trio.SocketStream) -> None:
    result = await s.socket.sendto(b"a", "h")
    assert_type(result, int)
