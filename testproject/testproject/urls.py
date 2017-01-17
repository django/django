from django.conf.urls import url
from chtest import views

urlpatterns = [url(r'^$', views.index)]

try:
    from chtest import consumers

    channel_routing = {"websocket.receive": consumers.ws_message}
except:
    pass
