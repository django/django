from thibaud.conf.urls.i18n import i18n_patterns
from thibaud.urls import path
from thibaud.views.generic import TemplateView

view = TemplateView.as_view(template_name="dummy.html")

urlpatterns = i18n_patterns(
    path("prefixed/", view, name="prefixed"),
)
