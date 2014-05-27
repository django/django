from freedom.conf.urls import url
from freedom.http import HttpResponse

urlpatterns = [
    url(r'^$', lambda request: HttpResponse('root is here')),
]
