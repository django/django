from django.conf.urls import url, include

from . import urlconf_inner


urlpatterns = [
    url(r'^test/me/$', urlconf_inner.inner_view, name='outer'),
    url(r'^inner_urlconf/', include(urlconf_inner.__name__))
]
