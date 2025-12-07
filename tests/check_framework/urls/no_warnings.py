from django.urls import include, path, re_path

urlpatterns = [
    path("foo/", lambda x: x, name="foo"),
    # This dollar is ok as it is escaped
    re_path(
        r"^\$",
        include(
            [
                path("bar/", lambda x: x, name="bar"),
            ]
        ),
    ),
]
