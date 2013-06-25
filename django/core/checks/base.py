# -*- coding: utf8 -*-


class _Error(object):
    def __init__(self, msg, **kwargs):
        assert 'hint' in kwargs
        self.msg = msg
        self.hint = kwargs['hint']
        self.obj = None

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr)
            for attr in ['msg', 'hint'])


class Error(_Error):
    pass


class Warning(_Error):
    pass
