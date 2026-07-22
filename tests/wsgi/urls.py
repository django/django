import asyncio
import threading

from django.core.signals import request_finished, request_started
from django.http import FileResponse, HttpResponse
from django.urls import path

event_loop_info = {}


def helloworld(request):
    return HttpResponse("Hello World!")


async def async_event_loop_info_view(request):
    event_loop_info["view_event_loop_id"] = id(asyncio.get_running_loop())
    event_loop_info["view_thread_id"] = threading.get_ident()
    return HttpResponse("Hello World!")


def cookie(request):
    response = HttpResponse("Hello World!")
    response.set_cookie("key", "value")
    return response


urlpatterns = [
    path("", helloworld),
    path("async_event_loop_id/", async_event_loop_info_view),
    path("cookie/", cookie),
    path("file/", lambda x: FileResponse(open(__file__, "rb"))),
]


async def store_start_event_loop_info(sender, **kwargs):
    event_loop_info["start_event_loop_id"] = id(asyncio.get_running_loop())
    event_loop_info["start_thread_id"] = threading.get_ident()


async def store_end_event_loop_info(sender, **kwargs):
    event_loop_info["end_event_loop_id"] = id(asyncio.get_running_loop())
    event_loop_info["end_thread_id"] = threading.get_ident()


request_started.connect(store_start_event_loop_info)
request_finished.connect(store_end_event_loop_info)
