from django.conf.urls import include, url

# special urls for flatpage test cases
urlpatterns = [
    url(r'^flatpage/', include('django.contrib.flatpages.urls')),
]

