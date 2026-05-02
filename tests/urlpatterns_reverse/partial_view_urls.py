from functools import partial

from django.urls import path


def view_with_args(request, arg=None):
    pass


urlpatterns = [
    path("partial/", partial(view_with_args, arg="x"), name="partial-view"),
]
