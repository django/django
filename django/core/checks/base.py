class _Error(object):
    def __init__(self, msg, **kwargs):
        assert 'hint' in kwargs
        self.msg = msg
        self.hint = kwargs['hint']


class Error(_Error):
    pass


class Warning(_Error):
    pass
