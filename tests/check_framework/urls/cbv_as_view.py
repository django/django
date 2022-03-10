from django.http import HttpResponse
from django.urls import path
from django.views import View


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
