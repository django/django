from django.urls import path

from . import views

urlpatterns = [
    path("view1/", views.View1.as_view(), name="view1"),
    path("view2/", views.View2.as_view(), name="view2"),
]
