urlpatterns = []

handler400 = __name__ + '.bad_handler'
handler403 = __name__ + '.bad_handler'
handler404 = __name__ + '.bad_handler'
handler500 = __name__ + '.bad_handler'


def bad_handler():
    pass
