import os

from django.conf.urls import url
from django.views.static import serve

here = os.path.dirname(__file__)

urlpatterns = [
    url(r'^custom_templates/(?P<path>.*)$', serve, {
        'document_root': os.path.join(here, 'custom_templates')}),
]
