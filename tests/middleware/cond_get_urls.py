from thibaud.http import HttpResponse
from thibaud.urls import path

urlpatterns = [
    path("", lambda request: HttpResponse("root is here")),
]
