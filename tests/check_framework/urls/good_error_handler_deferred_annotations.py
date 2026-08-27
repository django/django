from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http.request import HttpRequest

urlpatterns = []

handler400 = __name__ + ".good_handler_deferred_annotations"
handler403 = __name__ + ".good_handler_deferred_annotations"
handler404 = __name__ + ".good_handler_deferred_annotations"
handler500 = __name__ + ".good_handler_deferred_annotations"


def good_handler_deferred_annotations(request: HttpRequest, exception=None):
    pass
