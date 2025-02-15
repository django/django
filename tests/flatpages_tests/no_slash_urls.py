from thibaud.urls import include, path

urlpatterns = [
    path("flatpage", include("thibaud.contrib.flatpages.urls")),
]
