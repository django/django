import os

from django.urls import path
from django.views.static import serve

from . import views

here = os.path.dirname(__file__)

urlpatterns = [
    path(
        "custom_templates/<path:path>",
        serve,
        {"document_root": os.path.join(here, "custom_templates")},
    ),
    path(
        "bad_template_filename.tgz",
        views.template_bad_filename,
    ),
]
