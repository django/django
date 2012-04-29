import json

from django.core.exceptions import SuspiciousOperation
from django.core.signing import BadSignature

from django.contrib.formtools.wizard import storage


class CookieStorage(storage.BaseStorage):
    encoder = json.JSONEncoder(separators=(',', ':'))

    def __init__(self, *args, **kwargs):
        super(CookieStorage, self).__init__(*args, **kwargs)
        self.data = self.load_data()
        if self.data is None:
            self.init_data()

    def load_data(self):
        try:
            data = self.request.get_signed_cookie(self.prefix)
        except KeyError:
            data = None
        except BadSignature:
            raise SuspiciousOperation('WizardView cookie manipulated')
        if data is None:
            return None
        return json.loads(data, cls=json.JSONDecoder)

    def update_response(self, response):
        if self.data:
            response.set_signed_cookie(self.prefix, self.encoder.encode(self.data))
        else:
            response.delete_cookie(self.prefix)
