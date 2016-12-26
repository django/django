# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict, ErrorList, flatatt
from django.test import SimpleTestCase
from django.utils import six
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy


class FormsUtilsTestCase(SimpleTestCase):
    # Tests for forms/utils.py module.

    def test_flatatt(self):
        ###########
        # flatatt #
        ###########

        self.assertEqual(flatatt({'id': "header"}), ' id="header"')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this"}), ' class="news" title="Read this"')
        self.assertEqual(
            flatatt({'class': "news", 'title': "Read this", 'required': "required"}),
            ' class="news" required="required" title="Read this"'
        )
        self.assertEqual(
            flatatt({'class': "news", 'title': "Read this", 'required': True}),
            ' class="news" title="Read this" required'
        )
        self.assertEqual(
            flatatt({'class': "news", 'title': "Read this", 'required': False}),
            ' class="news" title="Read this"'
        )
        self.assertEqual(flatatt({'class': None}), '')
        self.assertEqual(flatatt({}), '')

    def test_flatatt_no_side_effects(self):
        """
        flatatt() does not modify the dict passed in.
        """
        attrs = {'foo': 'bar', 'true': True, 'false': False}
        attrs_copy = copy.copy(attrs)
        self.assertEqual(attrs, attrs_copy)

        first_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)
        self.assertEqual(first_run, ' foo="bar" true')

        second_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)

        self.assertEqual(first_run, second_run)

    def test_validation_error(self):
        ###################
        # ValidationError #
        ###################

        # Can take a string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError("There was an error.").messages)),
            '<ul class="errorlist"><li>There was an error.</li></ul>'
        )
        # Can take a unicode string.
        self.assertHTMLEqual(
            six.text_type(ErrorList(ValidationError("Not \u03C0.").messages)),
            '<ul class="errorlist"><li>Not π.</li></ul>'
        )
        # Can take a lazy string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(ugettext_lazy("Error.")).messages)),
            '<ul class="errorlist"><li>Error.</li></ul>'
        )
        # Can take a list.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(["Error one.", "Error two."]).messages)),
            '<ul class="errorlist"><li>Error one.</li><li>Error two.</li></ul>'
        )
        # Can take a dict.
        self.assertHTMLEqual(
            str(ErrorList(sorted(ValidationError({'error_1': "1. Error one.", 'error_2': "2. Error two."}).messages))),
            '<ul class="errorlist"><li>1. Error one.</li><li>2. Error two.</li></ul>'
        )
        # Can take a mixture in a list.
        self.assertHTMLEqual(
            str(ErrorList(sorted(ValidationError([
                "1. First error.",
                "2. Not \u03C0.",
                ugettext_lazy("3. Error."),
                {
                    'error_1': "4. First dict error.",
                    'error_2': "5. Second dict error.",
                },
            ]).messages))),
            '<ul class="errorlist">'
            '<li>1. First error.</li>'
            '<li>2. Not π.</li>'
            '<li>3. Error.</li>'
            '<li>4. First dict error.</li>'
            '<li>5. Second dict error.</li>'
            '</ul>'
        )

        @python_2_unicode_compatible
        class VeryBadError:
            def __str__(self):
                return "A very bad error."

        # Can take a non-string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(VeryBadError()).messages)),
            '<ul class="errorlist"><li>A very bad error.</li></ul>'
        )

        # Escapes non-safe input but not input marked safe.
        example = 'Example of link: <a href="http://www.example.com/">example</a>'
        self.assertHTMLEqual(
            str(ErrorList([example])),
            '<ul class="errorlist"><li>Example of link: '
            '&lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;</li></ul>'
        )
        self.assertHTMLEqual(
            str(ErrorList([mark_safe(example)])),
            '<ul class="errorlist"><li>Example of link: '
            '<a href="http://www.example.com/">example</a></li></ul>'
        )
        self.assertHTMLEqual(
            str(ErrorDict({'name': example})),
            '<ul class="errorlist"><li>nameExample of link: '
            '&lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;</li></ul>'
        )
        self.assertHTMLEqual(
            str(ErrorDict({'name': mark_safe(example)})),
            '<ul class="errorlist"><li>nameExample of link: '
            '<a href="http://www.example.com/">example</a></li></ul>'
        )

    def test_error_dict_copy(self):
        e = ErrorDict()
        e['__all__'] = ErrorList([
            ValidationError(
                message='message %(i)s',
                params={'i': 1},
            ),
            ValidationError(
                message='message %(i)s',
                params={'i': 2},
            ),
        ])

        e_copy = copy.copy(e)
        self.assertEqual(e, e_copy)
        self.assertEqual(e.as_data(), e_copy.as_data())

        e_deepcopy = copy.deepcopy(e)
        self.assertEqual(e, e_deepcopy)
        self.assertEqual(e.as_data(), e_copy.as_data())

    def test_error_dict_html_safe(self):
        e = ErrorDict()
        e['username'] = 'Invalid username.'
        self.assertTrue(hasattr(ErrorDict, '__html__'))
        self.assertEqual(force_text(e), e.__html__())

    def test_error_list_html_safe(self):
        e = ErrorList(['Invalid username.'])
        self.assertTrue(hasattr(ErrorList, '__html__'))
        self.assertEqual(force_text(e), e.__html__())
