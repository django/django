from typing import Any

from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie


class View1(View):
    @method_decorator(ensure_csrf_cookie)
    async def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        return await super().dispatch(request, *args, **kwargs)

    async def get(self, request: HttpRequest):
        return HttpResponse("hi")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class View2(View1):
    pass
