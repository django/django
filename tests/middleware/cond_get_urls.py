from django.conf.urls import url
from django.http import HttpResponse

urlpatterns = [
    url(r'^$', lambda request: HttpResponse('root is here')),
]
