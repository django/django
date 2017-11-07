from django.urls import path

urlpatterns = [
    path('(?P<named-group>\d+)', lambda x: x),
]
