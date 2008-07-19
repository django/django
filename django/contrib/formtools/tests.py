from django import forms
from django.contrib.formtools import preview
from django import http
from django.conf import settings
from django.test import TestCase

success_string = "Done was called!"
test_data = {'field1': u'foo',
             'field1_': u'asdf'}


class TestFormPreview(preview.FormPreview):

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)


class TestForm(forms.Form):
    field1 = forms.CharField()
    field1_ = forms.CharField()


class PreviewTests(TestCase):
    urls = 'django.contrib.formtools.test_urls'

    def setUp(self):
        # Create a FormPreview instance to share between tests
        self.preview = preview.FormPreview(TestForm)
        input_template = '<input type="hidden" name="%s" value="%s" />'
        self.input = input_template % (self.preview.unused_name('stage'), "%d")

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
        response = self.client.get('/test1/')
        stage = self.input % 1
        self.assertContains(response, stage, 1)

    def test_form_preview(self):
        """
        Test contrib.formtools.preview form preview rendering.

        Use the client library to POST to the form to see if a preview
        is returned.  If we do get a form back check that the hidden
        value is correctly managing the state of the form.

        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        test_data.update({'stage': 1})
        response = self.client.post('/test1/', test_data)
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
        test_data.update({'stage': 2})
        response = self.client.post('/test1/', test_data)
        self.failIfEqual(response.content, success_string)
        hash = self.preview.security_hash(None, TestForm(test_data))
        test_data.update({'hash': hash})
        response = self.client.post('/test1/', test_data)
        self.assertEqual(response.content, success_string)

