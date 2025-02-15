from thibaud.http import HttpResponse
from thibaud.urls import path

urlpatterns = [
    path("", lambda req: HttpResponse("example view")),
]
