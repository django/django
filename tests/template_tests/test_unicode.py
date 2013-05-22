# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template import Template, TemplateEncodingError, Context
from django.utils.safestring import SafeData
from django.utils import six
from django.utils.unittest import TestCase


class UnicodeTests(TestCase):
    def test_template(self):
        # Templates can be created from unicode strings.
        t1 = Template('ŠĐĆŽćžšđ {{ var }}')
        # Templates can also be created from bytestrings. These are assumed to
        # be encoded using UTF-8.
        s = b'\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91 {{ var }}'
        t2 = Template(s)
        s = b'\x80\xc5\xc0'
        self.assertRaises(TemplateEncodingError, Template, s)

        # Contexts can be constructed from unicode or UTF-8 bytestrings.
        c1 = Context({b"var": b"foo"})
        c2 = Context({"var": b"foo"})
        c3 = Context({b"var": "Đđ"})
        c4 = Context({"var": b"\xc4\x90\xc4\x91"})

        # Since both templates and all four contexts represent the same thing,
        # they all render the same (and are returned as unicode objects and
        # "safe" objects as well, for auto-escaping purposes).
        self.assertEqual(t1.render(c3), t2.render(c3))
        self.assertIsInstance(t1.render(c3), six.text_type)
        self.assertIsInstance(t1.render(c3), SafeData)
