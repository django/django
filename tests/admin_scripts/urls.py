from pathlib import Path

from django.urls import path
from django.views.static import serve

here = Path(__file__).parent

urlpatterns = [
    path(
        "custom_templates/<path:path>",
        serve,
        {"document_root": here / "custom_templates"},
    ),
]
