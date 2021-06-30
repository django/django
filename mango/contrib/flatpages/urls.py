from mango.contrib.flatpages import views
from mango.urls import path

urlpatterns = [
    path('<path:url>', views.flatpage, name='mango.contrib.flatpages.views.flatpage'),
]
