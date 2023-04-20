from django.urls import path

urlpatterns = [
    path(r"(?P<named_group>\d+)", lambda x: x),
]
