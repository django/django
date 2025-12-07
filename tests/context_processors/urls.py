from django.urls import path

from . import views

urlpatterns = [
    path("request_attrs/", views.request_processor),
    path("debug/", views.debug_processor),
    path("csp_nonce/", views.csp_nonce_processor),
]
