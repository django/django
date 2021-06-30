from mango.urls import include, path

urlpatterns = [
    path('flatpage', include('mango.contrib.flatpages.urls')),
]
