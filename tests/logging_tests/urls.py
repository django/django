from django.urls import path

from . import views

urlpatterns = [
    path("innocent/", views.innocent),
    path("redirect/", views.redirect),
    path("suspicious/", views.suspicious),
    path("suspicious_spec/", views.suspicious_spec),
    path("internal_server_error/", views.internal_server_error),
    path("uncaught_exception/", views.uncaught_exception),
    path("permission_denied/", views.permission_denied),
    path("multi_part_parser_error/", views.multi_part_parser_error),
    path("does_not_exist_raised/", views.does_not_exist_raised),
]
