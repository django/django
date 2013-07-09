# -*- coding: utf8 -*-


class BaseCheckError(object):
    def __init__(self, msg, hint, obj=None):
        self.msg = msg
        self.hint = hint
        self.obj = obj

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
            for attr in ['msg', 'hint', 'obj'])

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "<%s: msg=%r, hint=%r, obj=%r>" % \
            (self.__class__.__name__, self.msg, self.hint, self.obj)


class Error(BaseCheckError):
    pass


class Warning(BaseCheckError):
    pass
