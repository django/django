from django.conf.urls import url, patterns
from django.http import HttpResponse

def helloworld(request):
    return HttpResponse("Hello World!")

urlpatterns = patterns(
    "",
    url("^$", helloworld)
    )
