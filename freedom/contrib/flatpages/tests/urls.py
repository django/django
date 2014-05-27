from freedom.conf.urls import include, url

# special urls for flatpage test cases
urlpatterns = [
    url(r'^flatpage_root', include('freedom.contrib.flatpages.urls')),
    url(r'^accounts/', include('freedom.contrib.auth.urls')),
]
