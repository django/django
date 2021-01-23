from django.urls import path

from . import views

urlpatterns = [
    path('regular/', views.regular),
    path('async_regular/', views.async_regular),
    path('no_response_fbv/', views.no_response),
    path('no_response_cbv/', views.NoResponse()),
    path('streaming/', views.streaming),
    path('in_transaction/', views.in_transaction),
    path('not_in_transaction/', views.not_in_transaction),
    path('bad_request/', views.bad_request),
    path('suspicious/', views.suspicious),
    path('malformed_post/', views.malformed_post),
    path('httpstatus_enum/', views.httpstatus_enum),
    path('unawaited/', views.async_unawaited),
]
