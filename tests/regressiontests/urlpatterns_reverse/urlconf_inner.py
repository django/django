from django.conf.urls.defaults import *
from django.template import Template, Context
from django.http import HttpResponse

def inner_view(request):
    content = Template('{% url outer as outer_url %}outer:{{ outer_url }},'
                       '{% url inner as inner_url %}inner:{{ inner_url }}').render(Context())
    return HttpResponse(content)

urlpatterns = patterns('',
    url(r'^second_test/$', inner_view, name='inner'),
)