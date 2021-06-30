from mango.conf.urls.i18n import i18n_patterns
from mango.urls import path
from mango.views.generic import TemplateView

view = TemplateView.as_view(template_name='dummy.html')

urlpatterns = i18n_patterns(
    path('prefixed/', view, name='prefixed'),
)
