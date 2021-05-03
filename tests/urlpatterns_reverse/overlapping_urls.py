from django.urls import include, path

from .views import (
    overlapping_view1, overlapping_view2,
    overlapping_view3, not_overlapping_view
)


nested_urls = [
    path('overlapping/<slug:title>/', overlapping_view1, name='nested_overlapping_view1'),
    path('overlapping/<slug:author>/', overlapping_view2, name='nested_overlapping_view2'),
    path('overlapping/<slug:keyword>/', overlapping_view3, name='nested_overlapping_view3'),
    path('not-overlapping/<slug:keyword>/', not_overlapping_view, name='nested_not_overlapping_view'),
]

urlpatterns = [
    path('nested/', include(nested_urls)),
    path('overlapping/<slug:title>/', overlapping_view1, name='overlapping_view1'),
    path('overlapping/<slug:author>/', overlapping_view2, name='overlapping_view2'),
    path('overlapping/<slug:keyword>/', overlapping_view3, name='overlapping_view3'),
    path('not-overlapping/<slug:keyword>/', not_overlapping_view, name='not_overlapping_view'),
]