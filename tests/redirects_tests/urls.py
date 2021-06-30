from mango.http import HttpResponse
from mango.urls import path

urlpatterns = [
    path('', lambda req: HttpResponse('OK')),
]
