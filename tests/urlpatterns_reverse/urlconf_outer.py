from django.conf.urls import include, url

from . import urlconf_inner

urlpatterns = [
    url(r'^test/me/$', urlconf_inner.inner_view, name='outer'),
    url(r'^inner_urlconf/', include(urlconf_inner.__name__))
]
