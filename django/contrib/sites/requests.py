class RequestSite:
    """
    A class that shares the primary interface of Site (i.e., it has
    ``domain`` and ``name`` attributes) but gets its data from a Django
    HttpRequest object rather than from a database.

    The save() and delete() methods raise NotImplementedError.
    """
    def __init__(self, request):
        self.domain = self.name = request.get_host()

    def __str__(self):
        return self.domain

    def save(self, force_insert=False, force_update=False):
        raise NotImplementedError('RequestSite cannot be saved.')

    def delete(self):
        raise NotImplementedError('RequestSite cannot be deleted.')
