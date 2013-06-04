from django.conf.urls import patterns, url
from django.views.generic import TemplateView


view = TemplateView.as_view(template_name='dummy.html')

urlpatterns = patterns('',
    url(r'^foo/$', view, name='not-prefixed-included-url'),
)
