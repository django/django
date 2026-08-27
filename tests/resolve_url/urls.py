from django.urls import path

from .views import params_cbv, params_view, some_cbv, some_view

urlpatterns = [
    path("params/<slug:slug>/", params_view, name="params-view"),
    path("params-cbv/<int:pk>/", params_cbv, name="params-cbv"),
    path("some-url/", some_view, name="some-view"),
    path("some-cbv/", some_cbv, name="some-cbv"),
]
