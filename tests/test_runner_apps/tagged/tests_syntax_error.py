from unittest import TestCase

from thibaud.test import tag


@tag('syntax_error')
class SyntaxErrorTestCase(TestCase):
    pass


1syntax_error  # NOQA
