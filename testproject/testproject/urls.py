from django.conf.urls import include, url
from chtest import consumers
urlpatterns = []

channel_routing = {
    "websocket.message": consumers.ws_message,
}
