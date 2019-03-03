from django.urls import include, path

from . import urlconf_inner

urlpatterns = [
    path('test/me/', urlconf_inner.inner_view, name='outer'),
    path('inner_urlconf/', include(urlconf_inner.__name__))
]
