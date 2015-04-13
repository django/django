from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    # Example 1: Function Views
    #   Step 1. Import view above:  from {{ project_name }}.views import home
    #   Step 2. In this list:       url(r'^$', home, name='home'),
    # Example 2: Class-Based Views
    #   Step 1. Import view above:  from {{ project_name }}.views import Home
    #   Step 2. In this list:       url(r'^$', Home.as_view(), name='home'),
    # Example 3: Include URL Configuration
    #   Step 1. Import above:       from blog import urls as blog_urls
    #   Step 2. In this list:       url(r'^blog/', include(blog_urls)),

    url(r'^admin/', include(admin.site.urls)),
]
