from django.urls import path

from . import views

urlpatterns = [
    path("test_utils/get_person/<int:pk>/", views.get_person),
    path(
        "test_utils/no_template_used/", views.no_template_used, name="no_template_used"
    ),
]
