from django.http import Http404


class Resolver404(Http404):
    def __init__(self, msg, traceback=True):
        self.traceback = traceback
        super(Resolver404, self).__init__(msg)


class NoReverseMatch(Exception):
    pass
