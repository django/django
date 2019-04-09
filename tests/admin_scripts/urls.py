import os

from django.urls import path
from django.views.static import ServeStatic

here = os.path.dirname(__file__)

urlpatterns = [
    path('custom_templates/<path:path>', ServeStatic.as_view(document_root=os.path.join(here, 'custom_templates'))),
]
