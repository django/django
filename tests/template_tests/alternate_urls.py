from django.conf.urls import url

from . import views

urlpatterns = [
    # View returning a template response
    url(r'^template_response_view/$', views.template_response_view),

    # A view that can be hard to find...
    url(r'^snark/', views.snark, name='snark'),
]
