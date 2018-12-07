from django.urls import path

from . import views

urlpatterns = [
    # View returning a template response
    path('template_response_view/', views.template_response_view),

    # A view that can be hard to find...
    path('snark/', views.snark, name='snark'),
]
