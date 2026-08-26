from django.urls import include, path, re_path


def dummy_view(request): ...


urlpatterns = [
    path(
        route="nons/",
        view=include("admin_scripts.app_with_urls.urls_nons"),
    ),
    path(
        route="namespaced/",
        view=include("admin_scripts.app_with_urls.urls_namespaced", namespace="ns"),
    ),
    path(
        route="cbv/",
        view=include("admin_scripts.app_with_urls.urls_cbv"),
    ),
    re_path(
        r"^\.well-known/openid-configuration/?$",
        dummy_view,
        name="oidc-connect-discovery-info",
    ),
]
