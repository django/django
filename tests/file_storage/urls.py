from django.http import HttpResponse
from django.urls import path

urlpatterns = [
    path("", lambda req: HttpResponse("example view")),
]
