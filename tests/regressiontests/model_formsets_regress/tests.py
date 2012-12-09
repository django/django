from __future__ import absolute_import, unicode_literals

from django import forms
from django.forms.formsets import BaseFormSet, DELETION_FIELD_NAME
from django.forms.util import ErrorDict, ErrorList
from django.forms.models import modelform_factory, inlineformset_factory, modelformset_factory, BaseModelFormSet
from django.test import TestCase
from django.utils import six

from .models import User, UserSite, Restaurant, Manager, Network, Host


class InlineFormsetTests(TestCase):
    def test_formset_over_to_field(self):
        "A formset over a ForeignKey with a to_field can be saved. Regression for #10243"
        Form = modelform_factory(User)
        FormSet = inlineformset_factory(User, UserSite)

        # Instantiate the Form and FormSet to prove
        # you can create a form with no data
        form = Form()
        form_set = FormSet(instance=User())

        # Now create a new User and UserSite instance
        data = {
            'serial': '1',
            'username': 'apollo13',
            'usersite_set-TOTAL_FORMS': '1',
            'usersite_set-INITIAL_FORMS': '0',
            'usersite_set-MAX_NUM_FORMS': '0',
            'usersite_set-0-data': '10',
            'usersite_set-0-user': 'apollo13'
        }
        user = User()
        form = Form(data)
        if form.is_valid():
            user = form.save()
        else:
            self.fail('Errors found on form:%s' % form_set)

        form_set = FormSet(data, instance=user)
        if form_set.is_valid():
            form_set.save()
            usersite = UserSite.objects.all().values()
            self.assertEqual(usersite[0]['data'], 10)
            self.assertEqual(usersite[0]['user_id'], 'apollo13')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

        # Now update the UserSite instance
        data = {
            'usersite_set-TOTAL_FORMS': '1',
            'usersite_set-INITIAL_FORMS': '1',
            'usersite_set-MAX_NUM_FORMS': '0',
            'usersite_set-0-id': six.text_type(usersite[0]['id']),
            'usersite_set-0-data': '11',
            'usersite_set-0-user': 'apollo13'
        }
        form_set = FormSet(data, instance=user)
        if form_set.is_valid():
            form_set.save()
            usersite = UserSite.objects.all().values()
            self.assertEqual(usersite[0]['data'], 11)
            self.assertEqual(usersite[0]['user_id'], 'apollo13')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

        # Now add a new UserSite instance
        data = {
            'usersite_set-TOTAL_FORMS': '2',
            'usersite_set-INITIAL_FORMS': '1',
            'usersite_set-MAX_NUM_FORMS': '0',
            'usersite_set-0-id': six.text_type(usersite[0]['id']),
            'usersite_set-0-data': '11',
            'usersite_set-0-user': 'apollo13',
            'usersite_set-1-data': '42',
            'usersite_set-1-user': 'apollo13'
        }
        form_set = FormSet(data, instance=user)
        if form_set.is_valid():
            form_set.save()
            usersite = UserSite.objects.all().values().order_by('data')
            self.assertEqual(usersite[0]['data'], 11)
            self.assertEqual(usersite[0]['user_id'], 'apollo13')
            self.assertEqual(usersite[1]['data'], 42)
            self.assertEqual(usersite[1]['user_id'], 'apollo13')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

    def test_formset_over_inherited_model(self):
        "A formset over a ForeignKey with a to_field can be saved. Regression for #11120"
        Form = modelform_factory(Restaurant)
        FormSet = inlineformset_factory(Restaurant, Manager)

        # Instantiate the Form and FormSet to prove
        # you can create a form with no data
        form = Form()
        form_set = FormSet(instance=Restaurant())

        # Now create a new Restaurant and Manager instance
        data = {
            'name': "Guido's House of Pasta",
            'manager_set-TOTAL_FORMS': '1',
            'manager_set-INITIAL_FORMS': '0',
            'manager_set-MAX_NUM_FORMS': '0',
            'manager_set-0-name': 'Guido Van Rossum'
        }
        restaurant = User()
        form = Form(data)
        if form.is_valid():
            restaurant = form.save()
        else:
            self.fail('Errors found on form:%s' % form_set)

        form_set = FormSet(data, instance=restaurant)
        if form_set.is_valid():
            form_set.save()
            manager = Manager.objects.all().values()
            self.assertEqual(manager[0]['name'], 'Guido Van Rossum')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

        # Now update the Manager instance
        data = {
            'manager_set-TOTAL_FORMS': '1',
            'manager_set-INITIAL_FORMS': '1',
            'manager_set-MAX_NUM_FORMS': '0',
            'manager_set-0-id': six.text_type(manager[0]['id']),
            'manager_set-0-name': 'Terry Gilliam'
        }
        form_set = FormSet(data, instance=restaurant)
        if form_set.is_valid():
            form_set.save()
            manager = Manager.objects.all().values()
            self.assertEqual(manager[0]['name'], 'Terry Gilliam')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

        # Now add a new Manager instance
        data = {
            'manager_set-TOTAL_FORMS': '2',
            'manager_set-INITIAL_FORMS': '1',
            'manager_set-MAX_NUM_FORMS': '0',
            'manager_set-0-id': six.text_type(manager[0]['id']),
            'manager_set-0-name': 'Terry Gilliam',
            'manager_set-1-name': 'John Cleese'
        }
        form_set = FormSet(data, instance=restaurant)
        if form_set.is_valid():
            form_set.save()
            manager = Manager.objects.all().values().order_by('name')
            self.assertEqual(manager[0]['name'], 'John Cleese')
            self.assertEqual(manager[1]['name'], 'Terry Gilliam')
        else:
            self.fail('Errors found on formset:%s' % form_set.errors)

    def test_formset_with_none_instance(self):
        "A formset with instance=None can be created. Regression for #11872"
        Form = modelform_factory(User)
        FormSet = inlineformset_factory(User, UserSite)

        # Instantiate the Form and FormSet to prove
        # you can create a formset with an instance of None
        form = Form(instance=None)
        formset = FormSet(instance=None)

    def test_empty_fields_on_modelformset(self):
        "No fields passed to modelformset_factory should result in no fields on returned forms except for the id. See #14119."
        UserFormSet = modelformset_factory(User, fields=())
        formset = UserFormSet()
        for form in formset.forms:
            self.assertTrue('id' in form.fields)
            self.assertEqual(len(form.fields), 1)

    def test_save_as_new_with_new_inlines(self):
        """
        Existing and new inlines are saved with save_as_new.

        Regression for #14938.

        """
        efnet = Network.objects.create(name="EFNet")
        host1 = Host.objects.create(hostname="irc.he.net", network=efnet)

        HostFormSet = inlineformset_factory(Network, Host)

        # Add a new host, modify previous host, and save-as-new
        data = {
            'host_set-TOTAL_FORMS': '2',
            'host_set-INITIAL_FORMS': '1',
            'host_set-MAX_NUM_FORMS': '0',
            'host_set-0-id': six.text_type(host1.id),
            'host_set-0-hostname': 'tranquility.hub.dal.net',
            'host_set-1-hostname': 'matrix.de.eu.dal.net'
        }

        # To save a formset as new, it needs a new hub instance
        dalnet = Network.objects.create(name="DALnet")
        formset = HostFormSet(data, instance=dalnet, save_as_new=True)

        self.assertTrue(formset.is_valid())
        formset.save()
        self.assertQuerysetEqual(
            dalnet.host_set.order_by("hostname"),
            ["<Host: matrix.de.eu.dal.net>", "<Host: tranquility.hub.dal.net>"]
            )

    def test_initial_data(self):
        user = User.objects.create(username="bibi", serial=1)
        UserSite.objects.create(user=user, data=7)
        FormSet = inlineformset_factory(User, UserSite, extra=2)

        formset = FormSet(instance=user, initial=[{'data': 41}, {'data': 42}])
        self.assertEqual(formset.forms[0].initial['data'], 7)
        self.assertEqual(formset.extra_forms[0].initial['data'], 41)
        self.assertTrue('value="42"' in formset.extra_forms[1].as_p())


class FormsetTests(TestCase):
    def test_error_class(self):
        '''
        Test the type of Formset and Form error attributes
        '''
        Formset = modelformset_factory(User)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '0',
            'form-0-id': '',
            'form-0-username': 'apollo13',
            'form-0-serial': '1',
            'form-1-id': '',
            'form-1-username': 'apollo13',
            'form-1-serial': '2',
        }
        formset = Formset(data)
        # check if the returned error classes are correct
        # note: formset.errors returns a list as documented
        self.assertTrue(isinstance(formset.errors, list))
        self.assertTrue(isinstance(formset.non_form_errors(), ErrorList))
        for form in formset.forms:
            self.assertTrue(isinstance(form.errors, ErrorDict))
            self.assertTrue(isinstance(form.non_field_errors(), ErrorList))

    def test_initial_data(self):
        User.objects.create(username="bibi", serial=1)
        Formset = modelformset_factory(User, extra=2)
        formset = Formset(initial=[{'username': 'apollo11'}, {'username': 'apollo12'}])
        self.assertEqual(formset.forms[0].initial['username'], "bibi")
        self.assertEqual(formset.extra_forms[0].initial['username'], "apollo11")
        self.assertTrue('value="apollo12"' in formset.extra_forms[1].as_p())

    def test_extraneous_query_is_not_run(self):
        Formset = modelformset_factory(Network)
        data = {'test-TOTAL_FORMS': '1',
                'test-INITIAL_FORMS': '0',
                'test-MAX_NUM_FORMS': '',
                'test-0-name': 'Random Place', }
        with self.assertNumQueries(1):
            formset = Formset(data, prefix="test")
            formset.save()


class CustomWidget(forms.CharField):
    pass


class UserSiteForm(forms.ModelForm):
    class Meta:
        model = UserSite
        widgets = {'data': CustomWidget}


class Callback(object):

    def __init__(self):
        self.log = []

    def __call__(self, db_field, **kwargs):
        self.log.append((db_field, kwargs))
        return db_field.formfield(**kwargs)


class FormfieldCallbackTests(TestCase):
    """
    Regression for #13095: Using base forms with widgets
    defined in Meta should not raise errors.
    """

    def test_inlineformset_factory_default(self):
        Formset = inlineformset_factory(User, UserSite, form=UserSiteForm)
        form = Formset().forms[0]
        self.assertTrue(isinstance(form['data'].field.widget, CustomWidget))

    def test_modelformset_factory_default(self):
        Formset = modelformset_factory(UserSite, form=UserSiteForm)
        form = Formset().forms[0]
        self.assertTrue(isinstance(form['data'].field.widget, CustomWidget))

    def assertCallbackCalled(self, callback):
        id_field, user_field, data_field = UserSite._meta.fields
        expected_log = [
            (id_field, {}),
            (user_field, {}),
            (data_field, {'widget': CustomWidget}),
        ]
        self.assertEqual(callback.log, expected_log)

    def test_inlineformset_custom_callback(self):
        callback = Callback()
        inlineformset_factory(User, UserSite, form=UserSiteForm,
                              formfield_callback=callback)
        self.assertCallbackCalled(callback)

    def test_modelformset_custom_callback(self):
        callback = Callback()
        modelformset_factory(UserSite, form=UserSiteForm,
                             formfield_callback=callback)
        self.assertCallbackCalled(callback)


class BaseCustomDeleteFormSet(BaseFormSet):
    """
    A formset mix-in that lets a form decide if it's to be deleted.
    Works for BaseFormSets. Also works for ModelFormSets with #14099 fixed.

    form.should_delete() is called. The formset delete field is also suppressed.
    """
    def add_fields(self, form, index):
        super(BaseCustomDeleteFormSet, self).add_fields(form, index)
        self.can_delete = True
        if DELETION_FIELD_NAME in form.fields:
            del form.fields[DELETION_FIELD_NAME]

    def _should_delete_form(self, form):
        return hasattr(form, 'should_delete') and form.should_delete()


class FormfieldShouldDeleteFormTests(TestCase):
    """
    Regression for #14099: BaseModelFormSet should use ModelFormSet method _should_delete_form
    """

    class BaseCustomDeleteModelFormSet(BaseModelFormSet, BaseCustomDeleteFormSet):
        """ Model FormSet with CustomDelete MixIn """

    class CustomDeleteUserForm(forms.ModelForm):
        """ A model form with a 'should_delete' method """
        class Meta:
            model = User

        def should_delete(self):
            """ delete form if odd PK """
            return self.instance.pk % 2 != 0

    NormalFormset = modelformset_factory(User, form=CustomDeleteUserForm, can_delete=True)
    DeleteFormset = modelformset_factory(User, form=CustomDeleteUserForm, formset=BaseCustomDeleteModelFormSet)

    data = {
            'form-TOTAL_FORMS': '4',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '4',
            'form-0-username': 'John',
            'form-0-serial': '1',
            'form-1-username': 'Paul',
            'form-1-serial': '2',
            'form-2-username': 'George',
            'form-2-serial': '3',
            'form-3-username': 'Ringo',
            'form-3-serial': '5',
            }

    delete_all_ids = {
            'form-0-DELETE': '1',
            'form-1-DELETE': '1',
            'form-2-DELETE': '1',
            'form-3-DELETE': '1',
            }

    def test_init_database(self):
        """ Add test data to database via formset """
        formset = self.NormalFormset(self.data)
        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.save()), 4)

    def test_no_delete(self):
        """ Verify base formset doesn't modify database """
        # reload database
        self.test_init_database()

        # pass standard data dict & see none updated
        data = dict(self.data)
        data['form-INITIAL_FORMS'] = 4
        data.update(dict(
            ('form-%d-id' % i, user.pk)
            for i,user in enumerate(User.objects.all())
        ))
        formset = self.NormalFormset(data, queryset=User.objects.all())
        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.save()), 0)
        self.assertEqual(len(User.objects.all()), 4)

    def test_all_delete(self):
        """ Verify base formset honors DELETE field """
        # reload database
        self.test_init_database()

        # create data dict with all fields marked for deletion
        data = dict(self.data)
        data['form-INITIAL_FORMS'] = 4
        data.update(dict(
            ('form-%d-id' % i, user.pk)
            for i,user in enumerate(User.objects.all())
        ))
        data.update(self.delete_all_ids)
        formset = self.NormalFormset(data, queryset=User.objects.all())
        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.save()), 0)
        self.assertEqual(len(User.objects.all()), 0)

    def test_custom_delete(self):
        """ Verify DeleteFormset ignores DELETE field and uses form method """
        # reload database
        self.test_init_database()

        # Create formset with custom Delete function
        # create data dict with all fields marked for deletion
        data = dict(self.data)
        data['form-INITIAL_FORMS'] = 4
        data.update(dict(
            ('form-%d-id' % i, user.pk)
            for i,user in enumerate(User.objects.all())
        ))
        data.update(self.delete_all_ids)
        formset = self.DeleteFormset(data, queryset=User.objects.all())

        # verify two were deleted
        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.save()), 0)
        self.assertEqual(len(User.objects.all()), 2)

        # verify no "odd" PKs left
        odd_ids = [user.pk for user in User.objects.all() if user.pk % 2]
        self.assertEqual(len(odd_ids), 0)
