from django.contrib.formtools.wizard import storage


class SessionStorage(storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(SessionStorage, self).__init__(*args, **kwargs)
        if self.prefix not in self.request.session:
            self.init_data()

    def _get_data(self):
        self.request.session.modified = True
        return self.request.session[self.prefix]

    def _set_data(self, value):
        self.request.session[self.prefix] = value
        self.request.session.modified = True

    data = property(_get_data, _set_data)
