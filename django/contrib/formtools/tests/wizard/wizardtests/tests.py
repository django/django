from __future__ import unicode_literals

import os

from django import forms
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.formtools.wizard.views import CookieWizardView
from django.contrib.formtools.tests.wizard.forms import UserForm, UserFormSet
from django.utils._os import upath


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
                         {'name': ['This field is required.'],
                          'user': ['This field is required.']})

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
            'wizard_goto_step': response.context['wizard']['steps'].prev})
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

        # ticket #19025: `form` should be included in context
        form = response.context_data['wizard']['form']
        self.assertEqual(response.context_data['form'], form)            

    def test_form_finish(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form1')

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form2')

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'] = open(upath(__file__), 'rb')
        response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form3')

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'form4')

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)

        all_data = response.context['form_list']
        with open(upath(__file__), 'rb') as f:
            self.assertEqual(all_data[1]['file1'].read(), f.read())
        all_data[1]['file1'].close()
        del all_data[1]['file1']
        self.assertEqual(all_data, [
            {'name': 'Pony', 'thirsty': True, 'user': self.testuser},
            {'address1': '123 Main St', 'address2': 'Djangoland'},
            {'random_crap': 'blah blah'},
            [{'random_crap': 'blah blah'},
             {'random_crap': 'blah blah'}]])

    def test_cleaned_data(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)

        post_data = self.wizard_step_data[1]
        with open(upath(__file__), 'rb') as post_file:
            post_data['form2-file1'] = post_file
            response = self.client.post(self.wizard_url, post_data)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[2])
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[3])
        self.assertEqual(response.status_code, 200)

        all_data = response.context['all_cleaned_data']
        with open(upath(__file__), 'rb') as f:
            self.assertEqual(all_data['file1'].read(), f.read())
        all_data['file1'].close()
        del all_data['file1']
        self.assertEqual(all_data, {
            'name': 'Pony', 'thirsty': True, 'user': self.testuser,
            'address1': '123 Main St', 'address2': 'Djangoland',
            'random_crap': 'blah blah', 'formset-form4': [
                {'random_crap': 'blah blah'},
                {'random_crap': 'blah blah'}]})

    def test_manipulated_data(self):
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.wizard_url, self.wizard_step_data[0])
        self.assertEqual(response.status_code, 200)

        post_data = self.wizard_step_data[1]
        post_data['form2-file1'].close()
        post_data['form2-file1'] = open(upath(__file__), 'rb')
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
        post_data['form2-file1'].close()
        post_data['form2-file1'] = open(upath(__file__), 'rb')
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
        templates = os.path.join(os.path.dirname(upath(__file__)), 'templates')
        with self.settings(
                TEMPLATE_DIRS=list(settings.TEMPLATE_DIRS) + [templates]):
            response = self.client.get(self.wizard_url)
            self.assertTemplateUsed(response, 'other_wizard_form.html')


class WizardTestGenericViewInterface(TestCase):
    def test_get_context_data_inheritance(self):
        class TestWizard(CookieWizardView):
            """
            A subclass that implements ``get_context_data`` using the standard
            protocol for generic views (accept only **kwargs).

            See ticket #17148.
            """
            def get_context_data(self, **kwargs):
                context = super(TestWizard, self).get_context_data(**kwargs)
                context['test_key'] = 'test_value'
                return context

        factory = RequestFactory()
        view = TestWizard.as_view([forms.Form])

        response = view(factory.get('/'))
        self.assertEqual(response.context_data['test_key'], 'test_value')

    def test_get_context_data_with_mixin(self):
        class AnotherMixin(object):
            def get_context_data(self, **kwargs):
                context = super(AnotherMixin, self).get_context_data(**kwargs)
                context['another_key'] = 'another_value'
                return context

        class TestWizard(AnotherMixin, CookieWizardView):
            """
            A subclass that implements ``get_context_data`` using the standard
            protocol for generic views (accept only **kwargs).

            See ticket #17148.
            """
            def get_context_data(self, **kwargs):
                context = super(TestWizard, self).get_context_data(**kwargs)
                context['test_key'] = 'test_value'
                return context

        factory = RequestFactory()

        view = TestWizard.as_view([forms.Form])

        response = view(factory.get('/'))
        self.assertEqual(response.context_data['test_key'], 'test_value')
        self.assertEqual(response.context_data['another_key'], 'another_value')


class WizardFormKwargsOverrideTests(TestCase):
    def setUp(self):
        super(WizardFormKwargsOverrideTests, self).setUp()
        self.rf = RequestFactory()

        # Create two users so we can filter by is_staff when handing our
        # wizard a queryset keyword argument.
        self.normal_user = User.objects.create(username='test1', email='normal@example.com')
        self.staff_user = User.objects.create(username='test2', email='staff@example.com', is_staff=True)

    def test_instance_is_maintained(self):
        self.assertEqual(2, User.objects.count())
        queryset = User.objects.get(pk=self.staff_user.pk)

        class InstanceOverrideWizard(CookieWizardView):
            def get_form_kwargs(self, step):
                return {'instance': queryset}

        view = InstanceOverrideWizard.as_view([UserForm])
        response = view(self.rf.get('/'))

        form = response.context_data['wizard']['form']

        self.assertNotEqual(form.instance.pk, None)
        self.assertEqual(form.instance.pk, self.staff_user.pk)
        self.assertEqual('staff@example.com', form.initial.get('email', None))

    def test_queryset_is_maintained(self):
        queryset = User.objects.filter(pk=self.staff_user.pk)

        class QuerySetOverrideWizard(CookieWizardView):
            def get_form_kwargs(self, step):
                return {'queryset': queryset}

        view = QuerySetOverrideWizard.as_view([UserFormSet])
        response = view(self.rf.get('/'))

        formset = response.context_data['wizard']['form']

        self.assertNotEqual(formset.queryset, None)
        self.assertEqual(formset.initial_form_count(), 1)
        self.assertEqual(['staff@example.com'],
            list(formset.queryset.values_list('email', flat=True)))
