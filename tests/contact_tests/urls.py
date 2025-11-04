from django.urls import include, path

urlpatterns = [
    path("contact/", include("django.contrib.contact.urls")),
]
