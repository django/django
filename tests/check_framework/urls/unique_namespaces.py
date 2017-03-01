from django.conf.urls import include, url

common_url_patterns = ([
    url(r'^app-ns1/', include([])),
    url(r'^app-url/', include([])),
], 'common')

nested_url_patterns = ([
    url(r'^common/', include(common_url_patterns, namespace='nested')),
], 'nested')

urlpatterns = [
    url(r'^app-ns1-0/', include(common_url_patterns, namespace='app-include-1')),
    url(r'^app-ns1-1/', include(common_url_patterns, namespace='app-include-2')),
    # 'nested' is included twice but namespaced by nested-1 and nested-2.
    url(r'^app-ns1-2/', include(nested_url_patterns, namespace='nested-1')),
    url(r'^app-ns1-3/', include(nested_url_patterns, namespace='nested-2')),
    # namespaced URLs inside non-namespaced URLs.
    url(r'^app-ns1-4/', include([url(r'^abc/', include(common_url_patterns))])),
]
