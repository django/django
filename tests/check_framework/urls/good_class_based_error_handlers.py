from django.views.generic import View

urlpatterns = []


handler400 = View.as_view()
handler403 = View.as_view()
handler404 = View.as_view()
handler500 = View.as_view()
