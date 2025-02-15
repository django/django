from thibaud.contrib.flatpages import views
from thibaud.urls import path

urlpatterns = [
    path("flatpage/", views.flatpage, {"url": "/hardcoded/"}),
]
