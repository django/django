from django.conf.urls import patterns, url
from django.contrib import messages
from django.core.urlresolvers import reverse
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext, Template
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import FormView

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
def add_template_response(request, message_type):
    for msg in request.POST.getlist('messages'):
        getattr(messages, message_type)(request, msg)

    show_url = reverse('django.contrib.messages.tests.urls.show_template_response')
    return HttpResponseRedirect(show_url)

@never_cache
def show(request):
    t = Template(TEMPLATE)
    return HttpResponse(t.render(RequestContext(request)))

@never_cache
def show_template_response(request):
    return TemplateResponse(request, Template(TEMPLATE))


class ContactForm(forms.Form):
    name = forms.CharField(required=True)
    slug = forms.SlugField(required=True)


class ContactFormViewWithMsg(SuccessMessageMixin, FormView):
    form_class = ContactForm
    success_url = show
    success_message = "%(name)s was created successfully"


urlpatterns = patterns('',
    ('^add/(debug|info|success|warning|error)/$', add),
    url('^add/msg/$', ContactFormViewWithMsg.as_view(), name='add_success_msg'),
    ('^show/$', show),
    ('^template_response/add/(debug|info|success|warning|error)/$', add_template_response),
    ('^template_response/show/$', show_template_response),
)
