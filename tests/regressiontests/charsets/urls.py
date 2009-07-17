from django.conf.urls.defaults import *
import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^tutu/', include('tutu.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    (r'^accept_charset/', views.accept_charset),
    (r'^good_content_type/', views.good_content_type),
    (r'^bad_content_type/', views.bad_content_type),
    (r'^content_type_no_charset/', views.content_type_no_charset),
    (r'^basic_response/', views.basic_response),
    (r'^good_codec/', views.good_codec),
    (r'^bad_codec/', views.bad_codec),
    (r'^encode_response_content_type/', views.encode_response_content_type),
    (r'^encode_response_accept_charset/', views.encode_response_accept_charset),
)
