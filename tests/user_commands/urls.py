from django.urls import path

urlpatterns = [
    path('some/url/', lambda req:req, name='some_url'),
]
