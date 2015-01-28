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
