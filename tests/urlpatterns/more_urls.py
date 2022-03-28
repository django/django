from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r"^more/(?P<extra>\w+)/$",
        views.empty_view,
        {"sub-extra": True},
        name="inner-more",
    ),
]
