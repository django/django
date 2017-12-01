from django.conf.urls import include, url

from . import admin, custom_has_permission_admin, customadmin, views
from .test_autocomplete_view import site as autocomplete_site

urlpatterns = [
    url(r'^test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^test_admin/admin/secure-view/$', views.secure_view, name='secure_view'),
    url(r'^test_admin/admin/secure-view2/$', views.secure_view2, name='secure_view2'),
    url(r'^test_admin/admin/', admin.site.urls),
    url(r'^test_admin/admin2/', customadmin.site.urls),
    url(r'^test_admin/admin3/', (admin.site.get_urls(), 'admin', 'admin3'), {'form_url': 'pony'}),
    url(r'^test_admin/admin4/', customadmin.simple_site.urls),
    url(r'^test_admin/admin5/', admin.site2.urls),
    url(r'^test_admin/admin7/', admin.site7.urls),
    # All admin views accept `extra_context` to allow adding it like this:
    url(r'^test_admin/admin8/', (admin.site.get_urls(), 'admin', 'admin-extra-context'), {'extra_context': {}}),
    url(r'^test_admin/has_permission_admin/', custom_has_permission_admin.site.urls),
    url(r'^test_admin/autocomplete_admin/', autocomplete_site.urls),
]
