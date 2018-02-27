import uuid

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import Resolver404, path, resolve, reverse

from .converters import DynamicConverter
from .views import empty_view


@override_settings(ROOT_URLCONF='urlpatterns.path_urls')
class SimplifiedURLTests(SimpleTestCase):

    def test_path_lookup_without_parameters(self):
        match = resolve('/articles/2003/')
        self.assertEqual(match.url_name, 'articles-2003')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {})

    def test_path_lookup_with_typed_parameters(self):
        match = resolve('/articles/2015/')
        self.assertEqual(match.url_name, 'articles-year')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'year': 2015})

    def test_path_lookup_with_multiple_paramaters(self):
        match = resolve('/articles/2015/04/12/')
        self.assertEqual(match.url_name, 'articles-year-month-day')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'year': 2015, 'month': 4, 'day': 12})

    def test_two_variable_at_start_of_path_pattern(self):
        match = resolve('/en/foo/')
        self.assertEqual(match.url_name, 'lang-and-path')
        self.assertEqual(match.kwargs, {'lang': 'en', 'url': 'foo'})

    def test_path_reverse_without_parameter(self):
        url = reverse('articles-2003')
        self.assertEqual(url, '/articles/2003/')

    def test_path_reverse_with_parameter(self):
        url = reverse('articles-year-month-day', kwargs={'year': 2015, 'month': 4, 'day': 12})
        self.assertEqual(url, '/articles/2015/4/12/')

    @override_settings(ROOT_URLCONF='urlpatterns.path_base64_urls')
    def test_non_identical_converter_resolve(self):
        match = resolve('/base64/aGVsbG8=/')  # base64 of 'hello'
        self.assertEqual(match.url_name, 'base64')
        self.assertEqual(match.kwargs, {'value': b'hello'})

    @override_settings(ROOT_URLCONF='urlpatterns.path_base64_urls')
    def test_non_identical_converter_reverse(self):
        url = reverse('base64', kwargs={'value': b'hello'})
        self.assertEqual(url, '/base64/aGVsbG8=/')

    def test_path_inclusion_is_matchable(self):
        match = resolve('/included_urls/extra/something/')
        self.assertEqual(match.url_name, 'inner-extra')
        self.assertEqual(match.kwargs, {'extra': 'something'})

    def test_path_inclusion_is_reversable(self):
        url = reverse('inner-extra', kwargs={'extra': 'something'})
        self.assertEqual(url, '/included_urls/extra/something/')

    def test_invalid_converter(self):
        msg = "URL route 'foo/<nonexistent:var>/' uses invalid converter 'nonexistent'."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            path('foo/<nonexistent:var>/', empty_view)


@override_settings(ROOT_URLCONF='urlpatterns.converter_urls')
class ConverterTests(SimpleTestCase):

    def test_matching_urls(self):
        def no_converter(x):
            return x

        test_data = (
            ('int', {'0', '1', '01', 1234567890}, int),
            ('str', {'abcxyz'}, no_converter),
            ('path', {'allows.ANY*characters'}, no_converter),
            ('slug', {'abcxyz-ABCXYZ_01234567890'}, no_converter),
            ('uuid', {'39da9369-838e-4750-91a5-f7805cd82839'}, uuid.UUID),
        )
        for url_name, url_suffixes, converter in test_data:
            for url_suffix in url_suffixes:
                url = '/%s/%s/' % (url_name, url_suffix)
                with self.subTest(url=url):
                    match = resolve(url)
                    self.assertEqual(match.url_name, url_name)
                    self.assertEqual(match.kwargs, {url_name: converter(url_suffix)})
                    # reverse() works with string parameters.
                    string_kwargs = {url_name: url_suffix}
                    self.assertEqual(reverse(url_name, kwargs=string_kwargs), url)
                    # reverse() also works with native types (int, UUID, etc.).
                    if converter is not no_converter:
                        # The converted value might be different for int (a
                        # leading zero is lost in the conversion).
                        converted_value = match.kwargs[url_name]
                        converted_url = '/%s/%s/' % (url_name, converted_value)
                        self.assertEqual(reverse(url_name, kwargs={url_name: converted_value}), converted_url)

    def test_nonmatching_urls(self):
        test_data = (
            ('int', {'-1', 'letters'}),
            ('str', {'', '/'}),
            ('path', {''}),
            ('slug', {'', 'stars*notallowed'}),
            ('uuid', {
                '',
                '9da9369-838e-4750-91a5-f7805cd82839',
                '39da9369-838-4750-91a5-f7805cd82839',
                '39da9369-838e-475-91a5-f7805cd82839',
                '39da9369-838e-4750-91a-f7805cd82839',
                '39da9369-838e-4750-91a5-f7805cd8283',
            }),
        )
        for url_name, url_suffixes in test_data:
            for url_suffix in url_suffixes:
                url = '/%s/%s/' % (url_name, url_suffix)
                with self.subTest(url=url), self.assertRaises(Resolver404):
                    resolve(url)


class ParameterRestrictionTests(SimpleTestCase):
    def test_non_identifier_parameter_name_causes_exception(self):
        msg = (
            "URL route 'hello/<int:1>/' uses parameter name '1' which isn't "
            "a valid Python identifier."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            path(r'hello/<int:1>/', lambda r: None)

    def test_allows_non_ascii_but_valid_identifiers(self):
        # \u0394 is "GREEK CAPITAL LETTER DELTA", a valid identifier.
        p = path('hello/<str:\u0394>/', lambda r: None)
        match = p.resolve('hello/1/')
        self.assertEqual(match.kwargs, {'\u0394': '1'})


@override_settings(ROOT_URLCONF='urlpatterns.path_dynamic_urls')
class ConversionExceptionTests(SimpleTestCase):
    """How are errors in Converter.to_python() and to_url() handled?"""

    def test_resolve_value_error_means_no_match(self):
        @DynamicConverter.register_to_python
        def raises_value_error(value):
            raise ValueError()
        with self.assertRaises(Resolver404):
            resolve('/dynamic/abc/')

    def test_resolve_type_error_propogates(self):
        @DynamicConverter.register_to_python
        def raises_type_error(value):
            raise TypeError('This type error propagates.')
        with self.assertRaisesMessage(TypeError, 'This type error propagates.'):
            resolve('/dynamic/abc/')

    def test_reverse_value_error_propagates(self):
        @DynamicConverter.register_to_url
        def raises_value_error(value):
            raise ValueError('This value error propagates.')
        with self.assertRaisesMessage(ValueError, 'This value error propagates.'):
            reverse('dynamic', kwargs={'value': object()})
