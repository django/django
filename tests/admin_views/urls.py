from django.http import HttpResponse
from django.urls import include, path

from . import admin, custom_has_permission_admin, customadmin, views
from .test_autocomplete_view import site as autocomplete_site


def non_admin_view(request):
    return HttpResponse()


urlpatterns = [
    path('test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    path('test_admin/admin/secure-view/', views.secure_view, name='secure_view'),
    path('test_admin/admin/secure-view2/', views.secure_view2, name='secure_view2'),
    path('test_admin/admin/', admin.site.urls),
    path('test_admin/admin2/', customadmin.site.urls),
    path('test_admin/admin3/', (admin.site.get_urls(), 'admin', 'admin3'), {'form_url': 'pony'}),
    path('test_admin/admin4/', customadmin.simple_site.urls),
    path('test_admin/admin5/', admin.site2.urls),
    path('test_admin/admin6/', admin.site6.urls),
    path('test_admin/admin7/', admin.site7.urls),
    # All admin views accept `extra_context` to allow adding it like this:
    path('test_admin/admin8/', (admin.site.get_urls(), 'admin', 'admin-extra-context'), {'extra_context': {}}),
    path('test_admin/admin9/', admin.site9.urls),
    path('test_admin/admin10/', admin.site10.urls),
    path('test_admin/has_permission_admin/', custom_has_permission_admin.site.urls),
    path('test_admin/autocomplete_admin/', autocomplete_site.urls),
    # Shares the admin URL prefix.
    path('test_admin/admin/non_admin_view/', non_admin_view, name='non_admin'),
    path('test_admin/admin10/non_admin_view/', non_admin_view, name='non_admin10'),
]
