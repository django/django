import unittest
from django import forms
from django.contrib.formtools import preview, wizard, utils
from django import http
from django.test import TestCase

success_string = "Done was called!"

class TestFormPreview(preview.FormPreview):

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)

class TestForm(forms.Form):
    field1 = forms.CharField()
    field1_ = forms.CharField()
    bool1 = forms.BooleanField(required=False)

class PreviewTests(TestCase):
    urls = 'django.contrib.formtools.test_urls'

    def setUp(self):
        # Create a FormPreview instance to share between tests
        self.preview = preview.FormPreview(TestForm)
        input_template = '<input type="hidden" name="%s" value="%s" />'
        self.input = input_template % (self.preview.unused_name('stage'), "%d")
        self.test_data = {'field1':u'foo', 'field1_':u'asdf'}

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
        self.test_data.update({'stage': 1})
        response = self.client.post('/test1/', self.test_data)
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
        self.test_data.update({'stage':2})
        response = self.client.post('/test1/', self.test_data)
        self.failIfEqual(response.content, success_string)
        hash = self.preview.security_hash(None, TestForm(self.test_data))
        self.test_data.update({'hash': hash})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.content, success_string)

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
        self.test_data.update({'hash':hash, 'bool1':u'False'})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.content, success_string)

class SecurityHashTests(unittest.TestCase):

    def test_textfield_hash(self):
        """
        Regression test for #10034: the hash generation function should ignore
        leading/trailing whitespace so as to be friendly to broken browsers that
        submit it (usually in textareas).
        """
        class TestForm(forms.Form):
            name = forms.CharField()
            bio = forms.CharField()
        
        f1 = TestForm({'name': 'joe', 'bio': 'Nothing notable.'})
        f2 = TestForm({'name': '  joe', 'bio': 'Nothing notable.  '})
        hash1 = utils.security_hash(None, f1)
        hash2 = utils.security_hash(None, f2)
        self.assertEqual(hash1, hash2)

#
# FormWizard tests
#

class WizardPageOneForm(forms.Form):
    field = forms.CharField()

class WizardPageTwoForm(forms.Form):
    field = forms.CharField()

class WizardClass(wizard.FormWizard):
    def render_template(self, *args, **kw):
        return ""

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)

class DummyRequest(object):
    def __init__(self, POST=None):
        self.method = POST and "POST" or "GET"
        self.POST = POST

class WizardTests(TestCase):
    def test_step_starts_at_zero(self):
        """
        step should be zero for the first form
        """
        wizard = WizardClass([WizardPageOneForm, WizardPageTwoForm])
        request = DummyRequest()
        wizard(request)
        self.assertEquals(0, wizard.step)

    def test_step_increments(self):
        """
        step should be incremented when we go to the next page
        """
        wizard = WizardClass([WizardPageOneForm, WizardPageTwoForm])
        request = DummyRequest(POST={"0-field":"test", "wizard_step":"0"})
        response = wizard(request)
        self.assertEquals(1, wizard.step)

