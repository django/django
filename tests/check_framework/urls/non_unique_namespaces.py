from django.conf.urls import include, url

common_url_patterns = ([
    url(r'^app-ns1/', include([])),
    url(r'^app-url/', include([])),
], 'app-ns1')

urlpatterns = [
    url(r'^app-ns1-0/', include(common_url_patterns)),
    url(r'^app-ns1-1/', include(common_url_patterns)),
    url(r'^app-some-url/', include(([], 'app'), namespace='app-1')),
    url(r'^app-some-url-2/', include(([], 'app'), namespace='app-1'))
]
