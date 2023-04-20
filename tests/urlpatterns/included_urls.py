from django.urls import include, path

from . import views

urlpatterns = [
    path("extra/<extra>/", views.empty_view, name="inner-extra"),
    path("", include("urlpatterns.more_urls")),
]
