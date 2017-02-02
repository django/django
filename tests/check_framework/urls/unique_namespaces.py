from django.conf.urls import include, url

common_url_patterns = ([
    url(r'^app-ns1/', include([])),
    url(r'^app-url/', include([])),
], 'common')

urlpatterns = [
    url(r'^app-ns1-0/', include(common_url_patterns, namespace='app-include-1')),
    url(r'^app-ns1-1/', include(common_url_patterns, namespace='app-include-2'))
]
