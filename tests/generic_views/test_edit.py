from __future__ import unicode_literals

import warnings

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.test import (
    SimpleTestCase, TestCase, ignore_warnings, override_settings,
)
from django.test.client import RequestFactory
from django.utils.deprecation import RemovedInDjango110Warning
from django.views.generic.base import View
from django.views.generic.edit import CreateView, FormMixin, ModelFormMixin

from . import views
from .models import Artist, Author
from .test_forms import AuthorForm


class FormMixinTests(SimpleTestCase):
    def test_initial_data(self):
        """ Test instance independence of initial data dict (see #16138) """
        initial_1 = FormMixin().get_initial()
        initial_1['foo'] = 'bar'
        initial_2 = FormMixin().get_initial()
        self.assertNotEqual(initial_1, initial_2)

    def test_get_prefix(self):
        """ Test prefix can be set (see #18872) """
        test_string = 'test'

        rf = RequestFactory()
        get_request = rf.get('/')

        class TestFormMixin(FormMixin):
            request = get_request

        default_kwargs = TestFormMixin().get_form_kwargs()
        self.assertIsNone(default_kwargs.get('prefix'))

        set_mixin = TestFormMixin()
        set_mixin.prefix = test_string
        set_kwargs = set_mixin.get_form_kwargs()
        self.assertEqual(test_string, set_kwargs.get('prefix'))

    def test_get_form(self):
        class TestFormMixin(FormMixin):
            request = RequestFactory().get('/')

        self.assertIsInstance(
            TestFormMixin().get_form(forms.Form), forms.Form,
            'get_form() should use provided form class.'
        )

        class FormClassTestFormMixin(TestFormMixin):
            form_class = forms.Form

        self.assertIsInstance(
            FormClassTestFormMixin().get_form(), forms.Form,
            'get_form() should fallback to get_form_class() if none is provided.'
        )

    def test_get_form_missing_form_class_default_value(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always')

            class MissingDefaultValue(FormMixin):
                request = RequestFactory().get('/')
                form_class = forms.Form

                def get_form(self, form_class):
                    return form_class(**self.get_form_kwargs())
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0].category, RemovedInDjango110Warning)
        self.assertEqual(
            str(w[0].message),
            '`generic_views.test_edit.MissingDefaultValue.get_form` method '
            'must define a default value for its `form_class` argument.'
        )

        self.assertIsInstance(
            MissingDefaultValue().get_form(), forms.Form,
        )

    def test_get_context_data(self):
        class FormContext(FormMixin):
            request = RequestFactory().get('/')
            form_class = forms.Form

        self.assertIsInstance(FormContext().get_context_data()['form'], forms.Form)


@override_settings(ROOT_URLCONF='generic_views.urls')
class BasicFormTests(TestCase):

    def test_post_data(self):
        res = self.client.post('/contact/', {'name': "Me", 'message': "Hello"})
        self.assertRedirects(res, '/list/authors/')

    def test_late_form_validation(self):
        """
        A form can be marked invalid in the form_valid() method (#25548).
        """
        res = self.client.post('/late-validation/', {'name': "Me", 'message': "Hello"})
        self.assertFalse(res.context['form'].is_valid())


class ModelFormMixinTests(SimpleTestCase):
    def test_get_form(self):
        form_class = views.AuthorGetQuerySetFormView().get_form_class()
        self.assertEqual(form_class._meta.model, Author)

    def test_get_form_checks_for_object(self):
        mixin = ModelFormMixin()
        mixin.request = RequestFactory().get('/')
        self.assertEqual({'initial': {}, 'prefix': None},
                         mixin.get_form_kwargs())


@override_settings(ROOT_URLCONF='generic_views.urls')
class CreateViewTests(TestCase):

    def test_create(self):
        res = self.client.get('/edit/authors/create/')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.context['form'], forms.ModelForm)
        self.assertIsInstance(res.context['view'], View)
        self.assertNotIn('object', res.context)
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_form.html')

        res = self.client.post('/edit/authors/create/',
                        {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_create_invalid(self):
        res = self.client.post('/edit/authors/create/',
                        {'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_form.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertEqual(Author.objects.count(), 0)

    def test_create_with_object_url(self):
        res = self.client.post('/edit/artists/create/',
                        {'name': 'Rene Magritte'})
        self.assertEqual(res.status_code, 302)
        artist = Artist.objects.get(name='Rene Magritte')
        self.assertRedirects(res, '/detail/artist/%d/' % artist.pk)
        self.assertQuerysetEqual(Artist.objects.all(), ['<Artist: Rene Magritte>'])

    def test_create_with_redirect(self):
        res = self.client.post('/edit/authors/create/redirect/',
                            {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_create_with_interpolated_redirect(self):
        res = self.client.post(
            '/edit/authors/create/interpolate_redirect/',
            {'name': 'Randall Munroe', 'slug': 'randall-munroe'}
        )
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.first().pk
        self.assertRedirects(res, '/edit/author/%d/update/' % pk)
        # Also test with escaped chars in URL
        res = self.client.post(
            '/edit/authors/create/interpolate_redirect_nonascii/',
            {'name': 'John Doe', 'slug': 'john-doe'}
        )
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.get(name='John Doe').pk
        self.assertRedirects(res, '/%C3%A9dit/author/{}/update/'.format(pk))

    def test_create_with_special_properties(self):
        res = self.client.get('/edit/authors/create/special/')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.context['form'], views.AuthorForm)
        self.assertNotIn('object', res.context)
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/form.html')

        res = self.client.post('/edit/authors/create/special/',
                            {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        obj = Author.objects.get(slug='randall-munroe')
        self.assertRedirects(res, reverse('author_detail', kwargs={'pk': obj.pk}))
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_create_without_redirect(self):
        try:
            self.client.post('/edit/authors/create/naive/',
                {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
            self.fail('Should raise exception -- No redirect URL provided, and no get_absolute_url provided')
        except ImproperlyConfigured:
            pass

    def test_create_restricted(self):
        res = self.client.post('/edit/authors/create/restricted/',
            {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/accounts/login/?next=/edit/authors/create/restricted/')

    def test_create_view_with_restricted_fields(self):

        class MyCreateView(CreateView):
            model = Author
            fields = ['name']

        self.assertEqual(list(MyCreateView().get_form_class().base_fields),
                         ['name'])

    def test_create_view_all_fields(self):
        class MyCreateView(CreateView):
            model = Author
            fields = '__all__'

        self.assertEqual(list(MyCreateView().get_form_class().base_fields),
                         ['name', 'slug'])

    def test_create_view_without_explicit_fields(self):
        class MyCreateView(CreateView):
            model = Author

        message = (
            "Using ModelFormMixin (base class of MyCreateView) without the "
            "'fields' attribute is prohibited."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            MyCreateView().get_form_class()

    def test_define_both_fields_and_form_class(self):
        class MyCreateView(CreateView):
            model = Author
            form_class = AuthorForm
            fields = ['name']

        message = "Specifying both 'fields' and 'form_class' is not permitted."
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            MyCreateView().get_form_class()


@override_settings(ROOT_URLCONF='generic_views.urls')
class UpdateViewTests(TestCase):

    def test_update_post(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/%d/update/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.context['form'], forms.ModelForm)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'generic_views/author_form.html')
        self.assertEqual(res.context['view'].get_form_called_count, 1)

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/%d/update/' % a.pk,
                        {'name': 'Randall Munroe (xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (xkcd)>'])

    def test_update_invalid(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post('/edit/author/%d/update/' % a.pk,
                        {'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_form.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])
        self.assertEqual(res.context['view'].get_form_called_count, 1)

    def test_update_with_object_url(self):
        a = Artist.objects.create(name='Rene Magritte')
        res = self.client.post('/edit/artists/%d/update/' % a.pk,
                        {'name': 'Rene Magritte'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/detail/artist/%d/' % a.pk)
        self.assertQuerysetEqual(Artist.objects.all(), ['<Artist: Rene Magritte>'])

    def test_update_with_redirect(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post('/edit/author/%d/update/redirect/' % a.pk,
                        {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_update_with_interpolated_redirect(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post(
            '/edit/author/%d/update/interpolate_redirect/' % a.pk,
            {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'}
        )
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.first().pk
        self.assertRedirects(res, '/edit/author/%d/update/' % pk)
        # Also test with escaped chars in URL
        res = self.client.post(
            '/edit/author/%d/update/interpolate_redirect_nonascii/' % a.pk,
            {'name': 'John Doe', 'slug': 'john-doe'}
        )
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.get(name='John Doe').pk
        self.assertRedirects(res, '/%C3%A9dit/author/{}/update/'.format(pk))

    def test_update_with_special_properties(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/%d/update/special/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.context['form'], views.AuthorForm)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk=a.pk))
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/form.html')

        res = self.client.post('/edit/author/%d/update/special/' % a.pk,
                        {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/detail/author/%d/' % a.pk)
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])

    def test_update_without_redirect(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        # Should raise exception -- No redirect URL provided, and no
        # get_absolute_url provided
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/edit/author/%d/update/naive/' % a.pk,
                            {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})

    def test_update_get_object(self):
        a = Author.objects.create(
            pk=1,
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/update/')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.context['form'], forms.ModelForm)
        self.assertIsInstance(res.context['view'], View)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'generic_views/author_form.html')

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/update/',
                        {'name': 'Randall Munroe (xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (xkcd)>'])


@override_settings(ROOT_URLCONF='generic_views.urls')
class DeleteViewTests(TestCase):

    def test_delete_by_post(self):
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.get('/edit/author/%d/delete/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'generic_views/author_confirm_delete.html')

        # Deletion with POST
        res = self.client.post('/edit/author/%d/delete/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_by_delete(self):
        # Deletion with browser compatible DELETE method
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.delete('/edit/author/%d/delete/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_with_redirect(self):
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.post('/edit/author/%d/delete/redirect/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_delete_with_interpolated_redirect(self):
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.post('/edit/author/%d/delete/interpolate_redirect/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/edit/authors/create/?deleted=%d' % a.pk)
        self.assertQuerysetEqual(Author.objects.all(), [])
        # Also test with escaped chars in URL
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.post('/edit/author/{}/delete/interpolate_redirect_nonascii/'.format(a.pk))
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/%C3%A9dit/authors/create/?deleted={}'.format(a.pk))

    def test_delete_with_special_properties(self):
        a = Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.get('/edit/author/%d/delete/special/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk=a.pk))
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/confirm_delete.html')

        res = self.client.post('/edit/author/%d/delete/special/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, '/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_without_redirect(self):
        a = Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        # Should raise exception -- No redirect URL provided, and no
        # get_absolute_url provided
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/edit/author/%d/delete/naive/' % a.pk)
