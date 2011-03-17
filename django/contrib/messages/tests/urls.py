from django.conf.urls.defaults import *
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext, Template
from django.views.decorators.cache import never_cache


@never_cache
def add(request, message_type):
    # don't default to False here, because we want to test that it defaults
    # to False if unspecified
    fail_silently = request.POST.get('fail_silently', None)
    for msg in request.POST.getlist('messages'):
        if fail_silently is not None:
            getattr(messages, message_type)(request, msg,
                                            fail_silently=fail_silently)
        else:
            getattr(messages, message_type)(request, msg)
    show_url = reverse('django.contrib.messages.tests.urls.show')
    return HttpResponseRedirect(show_url)


@never_cache
def show(request):
    t = Template("""{% if messages %}
<ul class="messages">
    {% for message in messages %}
    <li{% if message.tags %} class="{{ message.tags }}"{% endif %}>
        {{ message }}
    </li>
    {% endfor %}
</ul>
{% endif %}""")
    return HttpResponse(t.render(RequestContext(request)))


urlpatterns = patterns('',
    ('^add/(debug|info|success|warning|error)/$', add),
    ('^show/$', show),
)
