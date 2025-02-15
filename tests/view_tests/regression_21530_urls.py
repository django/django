from thibaud.urls import path

from . import views

urlpatterns = [
    path("index/", views.index_page, name="index"),
]
