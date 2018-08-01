from django.urls import path

urlpatterns = [
    path(r'(?P<named-group>\d+)', lambda x: x),
]
