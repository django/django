from django.conf.urls import url

urlpatterns = [
    url(r'^some/url/$', lambda req:req, name='some_url'),
]
