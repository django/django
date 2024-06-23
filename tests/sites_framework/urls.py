from django.urls import re_path
from django.views.generic import TemplateView

urlpatterns = [
    re_path(
        r"^context_processors/$",
        TemplateView.as_view(template_name="templates/context_processor_test.html"),
    )
]
