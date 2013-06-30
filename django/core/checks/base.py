# -*- coding: utf8 -*-


class BaseError(object):
    def __init__(self, msg, hint, obj=None):
        self.msg = msg
        self.hint = hint
        self.obj = obj

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
            for attr in ['msg', 'hint', 'obj'])


class Error(BaseError):
    pass


class Warning(BaseError):
    pass
