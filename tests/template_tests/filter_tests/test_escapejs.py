from django.test import SimpleTestCase

from ..utils import render, setup


class EscapejsTests(SimpleTestCase):

    @setup({'escapejs01': '{{ a|escapejs }}'})
    def test_escapejs01(self):
        output = render('escapejs01', {'a': 'testing\r\njavascript \'string" <b>escaping</b>'})
        self.assertEqual(output, 'testing\\u000D\\u000Ajavascript '
                                 '\\u0027string\\u0022 \\u003Cb\\u003E'
                                 'escaping\\u003C/b\\u003E')

    @setup({'escapejs02': '{% autoescape off %}{{ a|escapejs }}{% endautoescape %}'})
    def test_escapejs02(self):
        output = render('escapejs02', {'a': 'testing\r\njavascript \'string" <b>escaping</b>'})
        self.assertEqual(output, 'testing\\u000D\\u000Ajavascript '
                                 '\\u0027string\\u0022 \\u003Cb\\u003E'
                                 'escaping\\u003C/b\\u003E')
