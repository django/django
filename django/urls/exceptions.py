from django.http import Http404


class Resolver404(Http404):
    def __init__(self, msg, traceback=True):
        # traceback changes the handling of Resolver404 when DEBUG=True
        # traceback=True results in a 500 error page with a traceback
        # traceback=False results in the standard 404 page
        self.traceback = traceback
        super(Resolver404, self).__init__(msg)


class NoReverseMatch(Exception):
    pass
