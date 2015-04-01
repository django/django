# Since this package contains a "jinja2" directory, this is required to
# silence an ImportWarning warning on Python 2.
from __future__ import absolute_import

import sys
from unittest import skipIf

from .test_dummy import TemplateStringsTests

# Jinja2 doesn't run on Python 3.2 because it uses u-prefixed unicode strings.
if sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 3):
    try:
        import jinja2
    except ImportError:
        jinja2 = None
        Jinja2 = None
    else:
        from django.template.backends.jinja2 import Jinja2
else:
    jinja2 = None
    Jinja2 = None


@skipIf(jinja2 is None, "this test requires jinja2")
class Jinja2Tests(TemplateStringsTests):

    engine_class = Jinja2
    backend_name = 'jinja2'
    options = {'keep_trailing_newline': True}

    def test_self_context(self):
        """
        Using 'self' in the context should not throw errors (#24538).
        """
        # self will be overridden to be a TemplateReference, so the self
        # variable will not come through. Attempting to use one though should
        # not throw an error.
        template = self.engine.from_string('hello {{ foo }}!')
        content = template.render(context={'self': 'self', 'foo': 'world'})
        self.assertEqual(content, 'hello world!')
