from thibaud.contrib.flatpages import views
from thibaud.urls import path

urlpatterns = [
    path("<path:url>", views.flatpage, name="thibaud.contrib.flatpages.views.flatpage"),
]
