from django.conf.urls.defaults import *
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext, Template
from django.template.response import TemplateResponse

TEMPLATE = """{% if messages %}
<ul class="messages">
    {% for message in messages %}
    <li{% if message.tags %} class="{{ message.tags }}"{% endif %}>
        {{ message }}
    </li>
    {% endfor %}
</ul>
{% endif %}
"""

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

def add_template_response(request, message_type):
    for msg in request.POST.getlist('messages'):
        getattr(messages, message_type)(request, msg)

    show_url = reverse('django.contrib.messages.tests.urls.show_template_response')
    return HttpResponseRedirect(show_url)

def show(request):
    t = Template(TEMPLATE)
    return HttpResponse(t.render(RequestContext(request)))

def show_template_response(request):
    return TemplateResponse(request, Template(TEMPLATE))

urlpatterns = patterns('',
    ('^add/(debug|info|success|warning|error)/$', add),
    ('^show/$', show),
    ('^template_response/add/(debug|info|success|warning|error)/$', add_template_response),
    ('^template_response/show/$', show_template_response),
)
