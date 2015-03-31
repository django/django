# Since this package contains a "jinja2" directory, this is required to
# silence an ImportWarning warning on Python 2.
from __future__ import absolute_import

from unittest import skipIf

from .test_dummy import TemplateStringsTests

try:
    import jinja2
except ImportError:
    jinja2 = None
    Jinja2 = None
else:
    from django.template.backends.jinja2 import Jinja2


@skipIf(jinja2 is None, "this test requires jinja2")
class Jinja2Tests(TemplateStringsTests):

    engine_class = Jinja2
    backend_name = 'jinja2'
    options = {'keep_trailing_newline': True}

    def test_self_context(self):
        """
        #24538 -- Using 'self' in the context should not throw errors
        """
        engine = Jinja2({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'django',
            'OPTIONS': {},
        })

        # self will be overridden to be a TemplateReference, so the self
        # variable will not come through. Attempting to use one though should
        # not throw an error.
        template = engine.from_string('hello {{ foo }}!')
        content = template.render(context={'self': 'self', 'foo': 'world'})
        self.assertEqual(content, 'hello world!')
