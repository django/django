from django.urls import path

from . import views

urlpatterns = [
    path("condition/", views.index),
    path("condition/last_modified/", views.last_modified_view1),
    path("condition/last_modified2/", views.last_modified_view2),
    path("condition/etag/", views.etag_view1),
    path("condition/etag2/", views.etag_view2),
    path("condition/unquoted_etag/", views.etag_view_unquoted),
    path("condition/weak_etag/", views.etag_view_weak),
    path("condition/no_etag/", views.etag_view_none),
]
