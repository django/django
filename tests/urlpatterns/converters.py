import base64


class Base64Converter:
    regex = r'[a-zA-Z0-9+/]*={0,2}'

    def to_python(self, value):
        return base64.b64decode(value)

    def to_url(self, value):
        return base64.b64encode(value).decode('ascii')


class DynamicConverter:
    _dynamic_to_python = None
    _dynamic_to_url = None

    @property
    def regex(self):
        return r'[0-9a-zA-Z]+'

    @regex.setter
    def regex(self):
        raise Exception("You can't modify the regular expression.")

    def to_python(self, value):
        return type(self)._dynamic_to_python(value)

    def to_url(self, value):
        return type(self)._dynamic_to_url(value)

    @classmethod
    def register_to_python(cls, value):
        cls._dynamic_to_python = value

    @classmethod
    def register_to_url(cls, value):
        cls._dynamic_to_url = value
