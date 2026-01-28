from django.urls import include, path
from django.utils.translation import gettext_lazy as _

from . import views

urlpatterns = [
    path(_("included_urls/"), include("urlpatterns.included_urls")),
    path(_("lazy/<slug:slug>/"), views.empty_view, name="lazy"),
]
