from django.conf.urls import patterns
from django.views.generic import TemplateView


urlpatterns = patterns('',
    (r'^context_processors/$',
     TemplateView.as_view(
        template_name='templates/context_processor_test.html')),)
