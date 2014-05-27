import os
from freedom.conf.urls import url
from freedom.utils._os import upath

here = os.path.dirname(upath(__file__))

urlpatterns = [
    url(r'^custom_templates/(?P<path>.*)$', 'freedom.views.static.serve', {
        'document_root': os.path.join(here, 'custom_templates')}),
]
