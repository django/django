from freedom.conf.urls import url
from freedom.template import Template, Context
from freedom.http import HttpResponse


def inner_view(request):
    content = Template('{% url "outer" as outer_url %}outer:{{ outer_url }},'
                       '{% url "inner" as inner_url %}inner:{{ inner_url }}').render(Context())
    return HttpResponse(content)

urlpatterns = [
    url(r'^second_test/$', inner_view, name='inner'),
]
