from django.contrib import admin
from django.urls import include, path

from . import views

ns_patterns = ([
    path('xview/func/', views.xview_dec(views.xview), name='func'),
], 'test')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admindocs/', include('django.contrib.admindocs.urls')),
    path('', include(ns_patterns, namespace='test')),
    path('xview/func/', views.xview_dec(views.xview)),
    path('xview/class/', views.xview_dec(views.XViewClass.as_view())),
    path('xview/callable_object/', views.xview_dec(views.XViewCallableObject())),
    path('xview/callable_object_without_xview/', views.XViewCallableObject()),
]
