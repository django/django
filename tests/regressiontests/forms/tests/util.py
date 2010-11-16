# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.forms.util import *
from django.utils.translation import ugettext_lazy
from django.utils.unittest import TestCase


class FormsUtilTestCase(TestCase):
        # Tests for forms/util.py module.

    def test_flatatt(self):
        ###########
        # flatatt #
        ###########

        self.assertEqual(flatatt({'id': "header"}), u' id="header"')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this"}), u' class="news" title="Read this"')
        self.assertEqual(flatatt({}), u'')

    def test_validation_error(self):
        ###################
        # ValidationError #
        ###################

        # Can take a string.
        self.assertEqual(str(ErrorList(ValidationError("There was an error.").messages)),
                         '<ul class="errorlist"><li>There was an error.</li></ul>')

        # Can take a unicode string.
        self.assertEqual(str(ErrorList(ValidationError(u"Not \u03C0.").messages)),
                         '<ul class="errorlist"><li>Not π.</li></ul>')

        # Can take a lazy string.
        self.assertEqual(str(ErrorList(ValidationError(ugettext_lazy("Error.")).messages)),
                         '<ul class="errorlist"><li>Error.</li></ul>')

        # Can take a list.
        self.assertEqual(str(ErrorList(ValidationError(["Error one.", "Error two."]).messages)),
                         '<ul class="errorlist"><li>Error one.</li><li>Error two.</li></ul>')

        # Can take a mixture in a list.
        self.assertEqual(str(ErrorList(ValidationError(["First error.", u"Not \u03C0.", ugettext_lazy("Error.")]).messages)),
                         '<ul class="errorlist"><li>First error.</li><li>Not π.</li><li>Error.</li></ul>')

        class VeryBadError:
            def __unicode__(self): return u"A very bad error."

        # Can take a non-string.
        self.assertEqual(str(ErrorList(ValidationError(VeryBadError()).messages)),
                         '<ul class="errorlist"><li>A very bad error.</li></ul>')

        # Escapes non-safe input but not input marked safe.
        example = 'Example of link: <a href="http://www.example.com/">example</a>'
        self.assertEqual(str(ErrorList([example])),
                         '<ul class="errorlist"><li>Example of link: &lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;</li></ul>')
        self.assertEqual(str(ErrorList([mark_safe(example)])),
                         '<ul class="errorlist"><li>Example of link: <a href="http://www.example.com/">example</a></li></ul>')
