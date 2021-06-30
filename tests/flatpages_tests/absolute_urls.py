from mango.contrib.flatpages import views
from mango.urls import path

urlpatterns = [
    path('flatpage/', views.flatpage, {'url': '/hardcoded/'}),
]
