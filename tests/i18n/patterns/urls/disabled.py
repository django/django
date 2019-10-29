from django.conf.urls.i18n import i18n_patterns
from django.urls import path
from django.views.generic import TemplateView

view = TemplateView.as_view(template_name='dummy.html')

urlpatterns = i18n_patterns(
    path('prefixed/', view, name='prefixed'),
)
