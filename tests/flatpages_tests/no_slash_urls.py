from django.urls import include, path

urlpatterns = [
    path('flatpage', include('django.contrib.flatpages.urls')),
]
