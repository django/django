from django import forms, http
from django.conf import settings
from django.test import TestCase
from django.template.response import TemplateResponse
from django.utils.importlib import import_module

from django.contrib.auth.models import User

from django.contrib.formtools.wizard.views import (WizardView,
                                                   SessionWizardView,
                                                   CookieWizardView)


class DummyRequest(http.HttpRequest):
    def __init__(self, POST=None):
        super(DummyRequest, self).__init__()
        self.method = POST and "POST" or "GET"
        if POST is not None:
            self.POST.update(POST)
        self.session = {}
        self._dont_enforce_csrf_checks = True


def get_request(*args, **kwargs):
    request = DummyRequest(*args, **kwargs)
    engine = import_module(settings.SESSION_ENGINE)
    request.session = engine.SessionStore(None)
    return request

class Step1(forms.Form):
    name = forms.CharField()

class Step2(forms.Form):
    name = forms.CharField()

class Step3(forms.Form):
    data = forms.CharField()

class CustomKwargsStep1(Step1):

    def __init__(self, test=None, *args, **kwargs):
        self.test = test
        return super(CustomKwargsStep1, self).__init__(*args, **kwargs)

class UserForm(forms.ModelForm):
    class Meta:
        model = User

UserFormSet = forms.models.modelformset_factory(User, form=UserForm, extra=2)

class TestWizard(WizardView):
    storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'

    def dispatch(self, request, *args, **kwargs):
        response = super(TestWizard, self).dispatch(request, *args, **kwargs)
        return response, self

    def get_form_kwargs(self, step, *args, **kwargs):
        kwargs = super(TestWizard, self).get_form_kwargs(step, *args, **kwargs)
        if step == 'kwargs_test':
            kwargs['test'] = True
        return kwargs

class FormTests(TestCase):
    def test_form_init(self):
        testform = TestWizard.get_initkwargs([Step1, Step2])
        self.assertEqual(testform['form_list'], {u'0': Step1, u'1': Step2})

        testform = TestWizard.get_initkwargs([('start', Step1), ('step2', Step2)])
        self.assertEqual(
            testform['form_list'], {u'start': Step1, u'step2': Step2})

        testform = TestWizard.get_initkwargs([Step1, Step2, ('finish', Step3)])
        self.assertEqual(
            testform['form_list'], {u'0': Step1, u'1': Step2, u'finish': Step3})

    def test_first_step(self):
        request = get_request()

        testform = TestWizard.as_view([Step1, Step2])
        response, instance = testform(request)
        self.assertEqual(instance.steps.current, u'0')

        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        response, instance = testform(request)

        self.assertEqual(instance.steps.current, 'start')

    def test_persistence(self):
        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        request = get_request({'test_wizard-current_step': 'start',
                               'name': 'data1'})
        response, instance = testform(request)
        self.assertEqual(instance.steps.current, 'start')

        instance.storage.current_step = 'step2'

        testform2 = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        request.POST = {'test_wizard-current_step': 'step2'}
        response, instance = testform2(request)
        self.assertEqual(instance.steps.current, 'step2')

    def test_form_condition(self):
        request = get_request()

        testform = TestWizard.as_view(
            [('start', Step1), ('step2', Step2), ('step3', Step3)],
            condition_dict={'step2': True})
        response, instance = testform(request)
        self.assertEqual(instance.get_next_step(), 'step2')

        testform = TestWizard.as_view(
            [('start', Step1), ('step2', Step2), ('step3', Step3)],
            condition_dict={'step2': False})
        response, instance = testform(request)
        self.assertEqual(instance.get_next_step(), 'step3')

    def test_form_kwargs(self):
        request = get_request()

        testform = TestWizard.as_view([('start', Step1),
            ('kwargs_test', CustomKwargsStep1)])
        response, instance = testform(request)

        self.assertEqual(instance.get_form_kwargs('start'), {})
        self.assertEqual(instance.get_form_kwargs('kwargs_test'), {'test': True})
        self.assertEqual(instance.get_form('kwargs_test').test, True)

    def test_form_prefix(self):
        request = get_request()

        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        response, instance = testform(request)

        self.assertEqual(instance.get_form_prefix(), 'start')
        self.assertEqual(instance.get_form_prefix('another'), 'another')

    def test_form_initial(self):
        request = get_request()

        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)],
            initial_dict={'start': {'name': 'value1'}})
        response, instance = testform(request)

        self.assertEqual(instance.get_form_initial('start'), {'name': 'value1'})
        self.assertEqual(instance.get_form_initial('step2'), {})

    def test_form_instance(self):
        request = get_request()
        the_instance = User()
        testform = TestWizard.as_view([('start', UserForm), ('step2', Step2)],
            instance_dict={'start': the_instance})
        response, instance = testform(request)

        self.assertEqual(
            instance.get_form_instance('start'),
            the_instance)
        self.assertEqual(
            instance.get_form_instance('non_exist_instance'),
            None)

    def test_formset_instance(self):
        request = get_request()
        the_instance1, created = User.objects.get_or_create(
            username='testuser1')
        the_instance2, created = User.objects.get_or_create(
            username='testuser2')
        testform = TestWizard.as_view([('start', UserFormSet), ('step2', Step2)],
            instance_dict={'start': User.objects.filter(username='testuser1')})
        response, instance = testform(request)

        self.assertEqual(list(instance.get_form_instance('start')), [the_instance1])
        self.assertEqual(instance.get_form_instance('non_exist_instance'), None)

        self.assertEqual(instance.get_form().initial_form_count(), 1)

    def test_done(self):
        request = get_request()

        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        response, instance = testform(request)

        self.assertRaises(NotImplementedError, instance.done, None)

    def test_revalidation(self):
        request = get_request()

        testform = TestWizard.as_view([('start', Step1), ('step2', Step2)])
        response, instance = testform(request)
        instance.render_done(None)
        self.assertEqual(instance.storage.current_step, 'start')


class SessionFormTests(TestCase):
    def test_init(self):
        request = get_request()
        testform = SessionWizardView.as_view([('start', Step1)])
        self.assertTrue(isinstance(testform(request), TemplateResponse))


class CookieFormTests(TestCase):
    def test_init(self):
        request = get_request()
        testform = CookieWizardView.as_view([('start', Step1)])
        self.assertTrue(isinstance(testform(request), TemplateResponse))
