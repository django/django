import asyncio
import contextlib
import threading
import time

from django.http import (
    FileResponse,
    HttpResponse,
    StreamingAcmgrHttpResponse,
    StreamingHttpResponse,
)
from django.urls import path
from django.views.decorators.csrf import csrf_exempt


def hello(request):
    name = request.GET.get("name") or "World"
    return HttpResponse("Hello %s!" % name)


def hello_with_delay(request):
    name = request.GET.get("name") or "World"
    time.sleep(1)
    return HttpResponse(f"Hello {name}!")


def hello_meta(request):
    return HttpResponse(
        "From %s" % request.META.get("HTTP_REFERER") or "",
        content_type=request.META.get("CONTENT_TYPE"),
    )


def sync_waiter(request):
    with sync_waiter.lock:
        sync_waiter.active_threads.add(threading.current_thread())
    sync_waiter.barrier.wait(timeout=0.5)
    return hello(request)


@csrf_exempt
def post_echo(request):
    if request.GET.get("echo"):
        return HttpResponse(request.body)
    else:
        return HttpResponse(status=204)


sync_waiter.active_threads = set()
sync_waiter.lock = threading.Lock()
sync_waiter.barrier = threading.Barrier(2)


async def streaming_inner(sleep_time):
    yield b"first\n"
    await asyncio.sleep(sleep_time)
    yield b"last\n"


async def streaming_view(request):
    sleep_time = float(request.GET["sleep"])
    return StreamingHttpResponse(streaming_inner(sleep_time))


class QueueIterator:
    def __init__(self, q, eof):
        self._q = q
        self._eof = eof

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._q.get()
        if msg is self._eof:
            raise StopAsyncIteration
        return msg


@contextlib.asynccontextmanager
async def streaming_acmgr_inner(sleep_time):
    eof = object()
    q = asyncio.Queue(0)

    async def push():
        await q.put(b"first\n")
        await asyncio.sleep(sleep_time)
        await q.put(b"last\n")
        await q.put(eof)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(push())
        yield QueueIterator(q=q, eof=eof)


async def streaming_acmgr_view(request):
    sleep_time = float(request.GET["sleep"])
    return StreamingAcmgrHttpResponse(streaming_acmgr_inner(sleep_time))


test_filename = __file__


urlpatterns = [
    path("", hello),
    path("file/", lambda x: FileResponse(open(test_filename, "rb"))),
    path("meta/", hello_meta),
    path("post/", post_echo),
    path("wait/", sync_waiter),
    path("delayed_hello/", hello_with_delay),
    path("streaming/", streaming_view),
    path("streaming_acmgr/", streaming_acmgr_view),
]
