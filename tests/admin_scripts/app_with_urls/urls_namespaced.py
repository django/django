from django.urls import path

from . import views

app_name = "app_with_urls"

urlpatterns = [
    path(
        route="unnamed",
        view=views.view_func_namespaced_unnamed,
    ),
    path(
        route="named",
        view=views.view_func_namespaced_named,
        name="named",
    ),
]
