# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import pickle
import re
import warnings

from django import http
from django.conf import settings
from django.contrib.formtools import preview, utils
from django.test import TestCase
from django.test.html import parse_html
from django.test.utils import override_settings
from django.utils._os import upath
from django.utils import unittest

from django.contrib.formtools.tests.wizard import *
from django.contrib.formtools.tests.forms import *

success_string = "Done was called!"
success_string_encoded = success_string.encode()

class TestFormPreview(preview.FormPreview):
    def get_context(self, request, form):
        context = super(TestFormPreview, self).get_context(request, form)
        context.update({'custom_context': True})
        return context

    def get_initial(self, request):
        return {'field1': 'Works!'}

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)

@override_settings(
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(upath(__file__)), 'templates'),
    ),
)
class PreviewTests(TestCase):
    urls = 'django.contrib.formtools.tests.urls'

    def setUp(self):
        super(PreviewTests, self).setUp()
        # Create a FormPreview instance to share between tests
        self.preview = preview.FormPreview(TestForm)
        input_template = '<input type="hidden" name="%s" value="%s" />'
        self.input = input_template % (self.preview.unused_name('stage'), "%d")
        self.test_data = {'field1': 'foo', 'field1_': 'asdf'}

    def test_unused_name(self):
        """
        Verifies name mangling to get uniue field name.
        """
        self.assertEqual(self.preview.unused_name('field1'), 'field1__')

    def test_form_get(self):
        """
        Test contrib.formtools.preview form retrieval.

        Use the client library to see if we can sucessfully retrieve
        the form (mostly testing the setup ROOT_URLCONF
        process). Verify that an additional  hidden input field
        is created to manage the stage.

        """
        response = self.client.get('/preview/')
        stage = self.input % 1
        self.assertContains(response, stage, 1)
        self.assertEqual(response.context['custom_context'], True)
        self.assertEqual(response.context['form'].initial, {'field1': 'Works!'})

    def test_form_preview(self):
        """
        Test contrib.formtools.preview form preview rendering.

        Use the client library to POST to the form to see if a preview
        is returned.  If we do get a form back check that the hidden
        value is correctly managing the state of the form.

        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage': 1, 'date1': datetime.date(2006, 10, 25)})
        response = self.client.post('/preview/', self.test_data)
        # Check to confirm stage is set to 2 in output form.
        stage = self.input % 2
        self.assertContains(response, stage, 1)

    def test_form_submit(self):
        """
        Test contrib.formtools.preview form submittal.

        Use the client library to POST to the form with stage set to 3
        to see if our forms done() method is called. Check first
        without the security hash, verify failure, retry with security
        hash and verify sucess.

        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage': 2, 'date1': datetime.date(2006, 10, 25)})
        response = self.client.post('/preview/', self.test_data)
        self.assertNotEqual(response.content, success_string_encoded)
        hash = self.preview.security_hash(None, TestForm(self.test_data))
        self.test_data.update({'hash': hash})
        response = self.client.post('/preview/', self.test_data)
        self.assertEqual(response.content, success_string_encoded)

    def test_bool_submit(self):
        """
        Test contrib.formtools.preview form submittal when form contains:
        BooleanField(required=False)

        Ticket: #6209 - When an unchecked BooleanField is previewed, the preview
        form's hash would be computed with no value for ``bool1``. However, when
        the preview form is rendered, the unchecked hidden BooleanField would be
        rendered with the string value 'False'. So when the preview form is
        resubmitted, the hash would be computed with the value 'False' for
        ``bool1``. We need to make sure the hashes are the same in both cases.

        """
        self.test_data.update({'stage':2})
        hash = self.preview.security_hash(None, TestForm(self.test_data))
        self.test_data.update({'hash': hash, 'bool1': 'False'})
        with warnings.catch_warnings(record=True):
            response = self.client.post('/preview/', self.test_data)
            self.assertEqual(response.content, success_string_encoded)

    def test_form_submit_good_hash(self):
        """
        Test contrib.formtools.preview form submittal, using a correct
        hash
        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage':2})
        response = self.client.post('/preview/', self.test_data)
        self.assertNotEqual(response.content, success_string_encoded)
        hash = utils.form_hmac(TestForm(self.test_data))
        self.test_data.update({'hash': hash})
        response = self.client.post('/preview/', self.test_data)
        self.assertEqual(response.content, success_string_encoded)


    def test_form_submit_bad_hash(self):
        """
        Test contrib.formtools.preview form submittal does not proceed
        if the hash is incorrect.
        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage':2})
        response = self.client.post('/preview/', self.test_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, success_string_encoded)
        hash = utils.form_hmac(TestForm(self.test_data)) + "bad"
        self.test_data.update({'hash': hash})
        response = self.client.post('/previewpreview/', self.test_data)
        self.assertNotEqual(response.content, success_string_encoded)


class FormHmacTests(unittest.TestCase):

    def test_textfield_hash(self):
        """
        Regression test for #10034: the hash generation function should ignore
        leading/trailing whitespace so as to be friendly to broken browsers that
        submit it (usually in textareas).
        """
        f1 = HashTestForm({'name': 'joe', 'bio': 'Speaking español.'})
        f2 = HashTestForm({'name': '  joe', 'bio': 'Speaking español.  '})
        hash1 = utils.form_hmac(f1)
        hash2 = utils.form_hmac(f2)
        self.assertEqual(hash1, hash2)

    def test_empty_permitted(self):
        """
        Regression test for #10643: the security hash should allow forms with
        empty_permitted = True, or forms where data has not changed.
        """
        f1 = HashTestBlankForm({})
        f2 = HashTestForm({}, empty_permitted=True)
        hash1 = utils.form_hmac(f1)
        hash2 = utils.form_hmac(f2)
        self.assertEqual(hash1, hash2)
