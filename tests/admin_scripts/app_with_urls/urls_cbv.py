from django.urls import path

from . import views

app_name = "app_with_urls_cbv"

urlpatterns = [
    path(
        route="unnamed",
        view=views.CBV.as_view(),
    ),
    path(
        route="named",
        view=views.CBV.as_view(),
        name="named",
    ),
]
