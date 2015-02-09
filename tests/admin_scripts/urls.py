import os

from django.conf.urls import url
from django.utils._os import upath
from django.views.static import serve

here = os.path.dirname(upath(__file__))

urlpatterns = [
    url(r'^custom_templates/(?P<path>.*)$', serve, {
        'document_root': os.path.join(here, 'custom_templates')}),
]
