from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^example_view/$', views.example_view),
    url(r'^model_view/$', views.model_view),
    url(r'^create_model_instance/$', views.create_model_instance),
    url(r'^environ_view/$', views.environ_view),
    url(r'^subview_calling_view/$', views.subview_calling_view),
    url(r'^subview/$', views.subview),
    url(r'^check_model_instance_from_subview/$', views.check_model_instance_from_subview),
]
