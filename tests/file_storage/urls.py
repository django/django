from freedom.conf.urls import url
from freedom.http import HttpResponse


urlpatterns = [
    url(r'^$', lambda req: HttpResponse('example view')),
]
