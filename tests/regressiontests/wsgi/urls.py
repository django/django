from django.conf.urls import url, patterns
from django.http import HttpResponse

def helloworld(request):
    return HttpResponse("Hello World!")

def will_raise(request):
    raise Exception()

urlpatterns = patterns(
    "",
    url("^$", helloworld),
    url("^exception$", will_raise)
    )
