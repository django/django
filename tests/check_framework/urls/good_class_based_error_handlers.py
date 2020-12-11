from django.views.generic import View


urlpatterns = []


class HandlerView(View):
    pass


handler400 = HandlerView.as_view()
handler403 = HandlerView.as_view()
handler404 = HandlerView.as_view()
handler500 = HandlerView.as_view()
