from __future__ import with_statement
import os

from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User


class WizardTests(object):
    urls = 'django.contrib.formtools.tests.wizard.wizardtests.urls'

    def setUp(self):
        self.testuser, created = User.objects.get_or_create(username='testuser1')
        self.wizard_step_data[0]['form1-user'] = self.testuser.pk

    def test_initial_call(self):
        response = self.client.get(self.wizard_url)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'form1')
        self.assertEqual(wizard['steps'].step0, 0)
        self.assertEqual(wizard['steps'].step1, 1)
        self.assertEqual(wizard['steps'].last, 'form4')
        self.assertEqual(wizard['steps'].prev, None)
        self.assertEqual(wizard['steps'].next, 'form2')
        self.assertEqual(wizard['steps'].count, 4)

    def test_form_post_error(self):
        response = self.client.post(self.wizard_url, self.wizard_step_1_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')
        self.assertEqual(response.context['wizard']['form'].errors,
                         {'name': [u'This field is required.'],
                          'user': [u'This field is required.']})

    def test_form_post_success(self):
        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'form2')
        self.assertEqual(wizard['steps'].step0, 1)
        self.assertEqual(wizard['steps'].prev, 'form1')
        self.assertEqual(wizard['steps'].next, 'form3')

    def test_form_stepback(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        response = self.client.post(self.wizard_url, {
            'wizard_prev_step': response.context['wizard']['steps'].prev})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

    def test_template_context(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')
        self.assertEqual(response.context.get('another_var', None), None)

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')
        self.assertEqual(response.context.get('another_var', None), True)

    def test_form_finish(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'] = open(__file__)
        response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form3')

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form4')

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)

        all_data = response.context['form_list']
        self.assertEqual(all_data[1]['file1'].read(), open(__file__).read())
        del all_data[1]['file1']
        self.assertEqual(all_data, [
            {'name': u'Pony', 'thirsty': True, 'user': self.testuser},
            {'address1': u'123 Main St', 'address2': u'Djangoland'},
            {'random_crap': u'blah blah'},
            [{'random_crap': u'blah blah'},
             {'random_crap': u'blah blah'}]])

    def test_cleaned_data(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'] = open(__file__)
        response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)

        all_data = response.context['all_cleaned_data']
        self.assertEqual(all_data['file1'].read(), open(__file__).read())
        del all_data['file1']
        self.assertEqual(all_data, {
            'name': u'Pony', 'thirsty': True, 'user': self.testuser,
            'address1': u'123 Main St', 'address2': u'Djangoland',
            'random_crap': u'blah blah', 'formset-form4': [
                {'random_crap': u'blah blah'},
                {'random_crap': u'blah blah'}]})

    def test_manipulated_data(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'] = open(__file__)
        response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)
        self.client.cookies.pop('sessionid', None)
        self.client.cookies.pop('wizard_cookie_contact_wizard', None)

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

    def test_form_refresh(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'] = open(__file__)
        response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form3')

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form4')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)


class SessionWizardTests(WizardTests, TestCase):
    wizard_url = '/wiz_session/'
    wizard_step_1_data = {
        'session_contact_wizard-current_step': 'form1',
    }
    wizard_step_data = (
        {
            'form1-name': 'Pony',
            'form1-thirsty': '2',
            'session_contact_wizard-current_step': 'form1',
        },
        {
            'form2-address1': '123 Main St',
            'form2-address2': 'Djangoland',
            'session_contact_wizard-current_step': 'form2',
        },
        {
            'form3-random_crap': 'blah blah',
            'session_contact_wizard-current_step': 'form3',
        },
        {
            'form4-INITIAL_FORMS': '0',
            'form4-TOTAL_FORMS': '2',
            'form4-MAX_NUM_FORMS': '0',
            'form4-0-random_crap': 'blah blah',
            'form4-1-random_crap': 'blah blah',
            'session_contact_wizard-current_step': 'form4',
        }
    )

class CookieWizardTests(WizardTests, TestCase):
    wizard_url = '/wiz_cookie/'
    wizard_step_1_data = {
        'cookie_contact_wizard-current_step': 'form1',
    }
    wizard_step_data = (
        {
            'form1-name': 'Pony',
            'form1-thirsty': '2',
            'cookie_contact_wizard-current_step': 'form1',
        },
        {
            'form2-address1': '123 Main St',
            'form2-address2': 'Djangoland',
            'cookie_contact_wizard-current_step': 'form2',
        },
        {
            'form3-random_crap': 'blah blah',
            'cookie_contact_wizard-current_step': 'form3',
        },
        {
            'form4-INITIAL_FORMS': '0',
            'form4-TOTAL_FORMS': '2',
            'form4-MAX_NUM_FORMS': '0',
            'form4-0-random_crap': 'blah blah',
            'form4-1-random_crap': 'blah blah',
            'cookie_contact_wizard-current_step': 'form4',
        }
    )

class WizardTestKwargs(TestCase):
    wizard_url = '/wiz_other_template/'
    wizard_step_1_data = {
        'cookie_contact_wizard-current_step': 'form1',
    }
    wizard_step_data = (
        {
            'form1-name': 'Pony',
            'form1-thirsty': '2',
            'cookie_contact_wizard-current_step': 'form1',
        },
        {
            'form2-address1': '123 Main St',
            'form2-address2': 'Djangoland',
            'cookie_contact_wizard-current_step': 'form2',
        },
        {
            'form3-random_crap': 'blah blah',
            'cookie_contact_wizard-current_step': 'form3',
        },
        {
            'form4-INITIAL_FORMS': '0',
            'form4-TOTAL_FORMS': '2',
            'form4-MAX_NUM_FORMS': '0',
            'form4-0-random_crap': 'blah blah',
            'form4-1-random_crap': 'blah blah',
            'cookie_contact_wizard-current_step': 'form4',
        }
    )
    urls = 'django.contrib.formtools.tests.wizard.wizardtests.urls'

    def setUp(self):
        self.testuser, created = User.objects.get_or_create(username='testuser1')
        self.wizard_step_data[0]['form1-user'] = self.testuser.pk

    def test_template(self):
        templates = os.path.join(os.path.dirname(__file__), 'templates')
        with self.settings(
                TEMPLATE_DIRS=list(settings.TEMPLATE_DIRS) + [templates]):
            response = self.client.get(self.wizard_url)
            self.assertTemplateUsed(response, 'other_wizard_form.html')
