from thibaud.http import HttpResponse
from thibaud.urls import path
from thibaud.views import View


class EmptyCBV(View):
    pass


class EmptyCallableView:
    def __call__(self, request, *args, **kwargs):
        return HttpResponse()


urlpatterns = [
    path("missing_as_view", EmptyCBV),
    path("has_as_view", EmptyCBV.as_view()),
    path("callable_class", EmptyCallableView()),
]
