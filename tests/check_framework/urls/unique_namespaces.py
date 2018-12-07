from django.urls import include, path

common_url_patterns = ([
    path('app-ns1/', include([])),
    path('app-url/', include([])),
], 'common')

nested_url_patterns = ([
    path('common/', include(common_url_patterns, namespace='nested')),
], 'nested')

urlpatterns = [
    path('app-ns1-0/', include(common_url_patterns, namespace='app-include-1')),
    path('app-ns1-1/', include(common_url_patterns, namespace='app-include-2')),
    # 'nested' is included twice but namespaced by nested-1 and nested-2.
    path('app-ns1-2/', include(nested_url_patterns, namespace='nested-1')),
    path('app-ns1-3/', include(nested_url_patterns, namespace='nested-2')),
    # namespaced URLs inside non-namespaced URLs.
    path('app-ns1-4/', include([path('abc/', include(common_url_patterns))])),
]
