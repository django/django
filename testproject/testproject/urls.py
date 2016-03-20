from django.conf.urls import  url
from chtest import consumers, views


urlpatterns = [
    url(r'^$', views.index),
]


channel_routing = {
    "websocket.receive": consumers.ws_message,
    "websocket.connect": consumers.ws_connect,
}
