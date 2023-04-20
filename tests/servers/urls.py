from django.urls import path

from . import views

urlpatterns = [
    path("example_view/", views.example_view),
    path("streaming_example_view/", views.streaming_example_view),
    path("model_view/", views.model_view),
    path("create_model_instance/", views.create_model_instance),
    path("environ_view/", views.environ_view),
    path("subview_calling_view/", views.subview_calling_view),
    path("subview/", views.subview),
    path("check_model_instance_from_subview/", views.check_model_instance_from_subview),
    path("method_view/", views.method_view),
]
