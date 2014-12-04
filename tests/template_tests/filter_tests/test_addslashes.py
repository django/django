from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class AddslashesTests(SimpleTestCase):

    @setup({'addslashes01': '{% autoescape off %}{{ a|addslashes }} {{ b|addslashes }}{% endautoescape %}'})
    def test_addslashes01(self):
        output = render('addslashes01', {"a": "<a>'", "b": mark_safe("<a>'")})
        self.assertEqual(output, r"<a>\' <a>\'")

    @setup({'addslashes02': '{{ a|addslashes }} {{ b|addslashes }}'})
    def test_addslashes02(self):
        output = render('addslashes02', {"a": "<a>'", "b": mark_safe("<a>'")})
        self.assertEqual(output, r"&lt;a&gt;\&#39; <a>\'")
