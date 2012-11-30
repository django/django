# -*- coding: utf-8 -*-
"""
URL dispatcher config for {{ project_name|title }} Django project.

.. seealso::
    http://docs.djangoproject.com/en/dev/topics/http/urls/
"""
from django.conf.urls import patterns, include, url

# Uncomment to enable the Django admin interface:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment to enable the Django admin interface and documentation:
    #url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    #url(r'^admin/', include(admin.site.urls)),
)
