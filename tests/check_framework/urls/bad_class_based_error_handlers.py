urlpatterns = []


class HandlerView:

    def view(self):
        pass

    @classmethod
    def as_view(cls):
        return cls.view


handler400 = HandlerView.as_view()
handler403 = HandlerView.as_view()
handler404 = HandlerView.as_view()
handler500 = HandlerView.as_view()
