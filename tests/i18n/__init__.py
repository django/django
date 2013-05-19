from threading import local


class TransRealMixin(object):
    """This is the only way to reset the translation machinery. Otherwise
    the test suite occasionally fails because of global state pollution
    between tests."""
    def flush_caches(self):
        from django.utils.translation import trans_real
        trans_real._translations = {}
        trans_real._active = local()
        trans_real._default = None
        trans_real._accepted = {}
        trans_real._checked_languages = {}

    def tearDown(self):
        self.flush_caches()
        super(TransRealMixin, self).tearDown()
