from django.conf.urls import include, url

urlpatterns = [
    url(r'^foo/', lambda x: x, name='foo'),
    # This dollar is ok as it is escaped
    url(r'^\$', include([
        url(r'^bar/$', lambda x: x, name='bar'),
    ])),
]
