import string
import uuid

from django.conf.urls import url as conf_url
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import NoReverseMatch, Resolver404, path, resolve, reverse
from django.utils.deprecation import RemovedInDjango40Warning

from .converters import DynamicConverter
from .views import empty_view

included_kwargs = {'base': b'hello', 'value': b'world'}
converter_test_data = (
    # ('url', ('url_name', 'app_name', {kwargs})),
    # aGVsbG8= is 'hello' encoded in base64.
    ('/base64/aGVsbG8=/', ('base64', '', {'value': b'hello'})),
    ('/base64/aGVsbG8=/subpatterns/d29ybGQ=/', ('subpattern-base64', '', included_kwargs)),
    ('/base64/aGVsbG8=/namespaced/d29ybGQ=/', ('subpattern-base64', 'namespaced-base64', included_kwargs)),
)


@override_settings(ROOT_URLCONF='urlpatterns.path_urls')
class SimplifiedURLTests(SimpleTestCase):

    def test_path_lookup_without_parameters(self):
        match = resolve('/articles/2003/')
        self.assertEqual(match.url_name, 'articles-2003')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {})
        self.assertEqual(match.route, 'articles/2003/')

    def test_path_lookup_with_typed_parameters(self):
        match = resolve('/articles/2015/')
        self.assertEqual(match.url_name, 'articles-year')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'year': 2015})
        self.assertEqual(match.route, 'articles/<int:year>/')

    def test_path_lookup_with_multiple_parameters(self):
        match = resolve('/articles/2015/04/12/')
        self.assertEqual(match.url_name, 'articles-year-month-day')
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'year': 2015, 'month': 4, 'day': 12})
        self.assertEqual(match.route, 'articles/<int:year>/<int:month>/<int:day>/')

    def test_two_variable_at_start_of_path_pattern(self):
        match = resolve('/en/foo/')
        self.assertEqual(match.url_name, 'lang-and-path')
        self.assertEqual(match.kwargs, {'lang': 'en', 'url': 'foo'})
        self.assertEqual(match.route, '<lang>/<path:url>/')

    def test_re_path(self):
        match = resolve('/regex/1/')
        self.assertEqual(match.url_name, 'regex')
        self.assertEqual(match.kwargs, {'pk': '1'})
        self.assertEqual(match.route, '^regex/(?P<pk>[0-9]+)/$')

    def test_re_path_with_optional_parameter(self):
        for url, kwargs in (
            ('/regex_optional/1/2/', {'arg1': '1', 'arg2': '2'}),
            ('/regex_optional/1/', {'arg1': '1'}),
        ):
            with self.subTest(url=url):
                match = resolve(url)
                self.assertEqual(match.url_name, 'regex_optional')
                self.assertEqual(match.kwargs, kwargs)
                self.assertEqual(
                    match.route,
                    r'^regex_optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?',
                )

    def test_re_path_with_missing_optional_parameter(self):
        match = resolve('/regex_only_optional/')
        self.assertEqual(match.url_name, 'regex_only_optional')
        self.assertEqual(match.kwargs, {})
        self.assertEqual(match.args, ())
        self.assertEqual(
            match.route,
            r'^regex_only_optional/(?:(?P<arg1>\d+)/)?',
        )

    def test_path_lookup_with_inclusion(self):
        match = resolve('/included_urls/extra/something/')
        self.assertEqual(match.url_name, 'inner-extra')
        self.assertEqual(match.route, 'included_urls/extra/<extra>/')

    def test_path_lookup_with_empty_string_inclusion(self):
        match = resolve('/more/99/')
        self.assertEqual(match.url_name, 'inner-more')
        self.assertEqual(match.route, r'^more/(?P<extra>\w+)/$')

    def test_path_lookup_with_double_inclusion(self):
        match = resolve('/included_urls/more/some_value/')
        self.assertEqual(match.url_name, 'inner-more')
        self.assertEqual(match.route, r'included_urls/more/(?P<extra>\w+)/$')

    def test_path_reverse_without_parameter(self):
        url = reverse('articles-2003')
        self.assertEqual(url, '/articles/2003/')

    def test_path_reverse_with_parameter(self):
        url = reverse('articles-year-month-day', kwargs={'year': 2015, 'month': 4, 'day': 12})
        self.assertEqual(url, '/articles/2015/4/12/')

    @override_settings(ROOT_URLCONF='urlpatterns.path_base64_urls')
    def test_converter_resolve(self):
        for url, (url_name, app_name, kwargs) in converter_test_data:
            with self.subTest(url=url):
                match = resolve(url)
                self.assertEqual(match.url_name, url_name)
                self.assertEqual(match.app_name, app_name)
                self.assertEqual(match.kwargs, kwargs)

    @override_settings(ROOT_URLCONF='urlpatterns.path_base64_urls')
    def test_converter_reverse(self):
        for expected, (url_name, app_name, kwargs) in converter_test_data:
            if app_name:
                url_name = '%s:%s' % (app_name, url_name)
            with self.subTest(url=url_name):
                url = reverse(url_name, kwargs=kwargs)
                self.assertEqual(url, expected)

    @override_settings(ROOT_URLCONF='urlpatterns.path_base64_urls')
    def test_converter_reverse_with_second_layer_instance_namespace(self):
        kwargs = included_kwargs.copy()
        kwargs['last_value'] = b'world'
        url = reverse('instance-ns-base64:subsubpattern-base64', kwargs=kwargs)
        self.assertEqual(url, '/base64/aGVsbG8=/subpatterns/d29ybGQ=/d29ybGQ=/')

    def test_path_inclusion_is_matchable(self):
        match = resolve('/included_urls/extra/something/')
        self.assertEqual(match.url_name, 'inner-extra')
        self.assertEqual(match.kwargs, {'extra': 'something'})

    def test_path_inclusion_is_reversible(self):
        url = reverse('inner-extra', kwargs={'extra': 'something'})
        self.assertEqual(url, '/included_urls/extra/something/')

    def test_invalid_converter(self):
        msg = "URL route 'foo/<nonexistent:var>/' uses invalid converter 'nonexistent'."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            path('foo/<nonexistent:var>/', empty_view)

    def test_whitespace_in_route(self):
        msg = (
            "URL route 'space/<int:num>/extra/<str:%stest>' cannot contain "
            "whitespace in angle brackets <…>"
        )
        for whitespace in string.whitespace:
            with self.subTest(repr(whitespace)):
                with self.assertRaisesMessage(ImproperlyConfigured, msg % whitespace):
                    path('space/<int:num>/extra/<str:%stest>' % whitespace, empty_view)
        # Whitespaces are valid in paths.
        p = path('space%s/<int:num>/' % string.whitespace, empty_view)
        match = p.resolve('space%s/1/' % string.whitespace)
        self.assertEqual(match.kwargs, {'num': 1})

    def test_path_trailing_newlines(self):
        tests = [
            '/articles/2003/\n',
            '/articles/2010/\n',
            '/en/foo/\n',
            '/included_urls/extra/\n',
            '/regex/1/\n',
            '/users/1/\n',
        ]
        for url in tests:
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url)


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


@override_settings(ROOT_URLCONF='urlpatterns.path_same_name_urls')
class SameNameTests(SimpleTestCase):
    def test_matching_urls_same_name(self):
        @DynamicConverter.register_to_url
        def requires_tiny_int(value):
            if value > 5:
                raise ValueError
            return value

        tests = [
            ('number_of_args', [
                ([], {}, '0/'),
                ([1], {}, '1/1/'),
            ]),
            ('kwargs_names', [
                ([], {'a': 1}, 'a/1/'),
                ([], {'b': 1}, 'b/1/'),
            ]),
            ('converter', [
                (['a/b'], {}, 'path/a/b/'),
                (['a b'], {}, 'str/a%20b/'),
                (['a-b'], {}, 'slug/a-b/'),
                (['2'], {}, 'int/2/'),
                (
                    ['39da9369-838e-4750-91a5-f7805cd82839'],
                    {},
                    'uuid/39da9369-838e-4750-91a5-f7805cd82839/'
                ),
            ]),
            ('regex', [
                (['ABC'], {}, 'uppercase/ABC/'),
                (['abc'], {}, 'lowercase/abc/'),
            ]),
            ('converter_to_url', [
                ([6], {}, 'int/6/'),
                ([1], {}, 'tiny_int/1/'),
            ]),
        ]
        for url_name, cases in tests:
            for args, kwargs, url_suffix in cases:
                expected_url = '/%s/%s' % (url_name, url_suffix)
                with self.subTest(url=expected_url):
                    self.assertEqual(
                        reverse(url_name, args=args, kwargs=kwargs),
                        expected_url,
                    )


class ParameterRestrictionTests(SimpleTestCase):
    def test_integer_parameter_name_causes_exception(self):
        msg = (
            "URL route 'hello/<int:1>/' uses parameter name '1' which isn't "
            "a valid Python identifier."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            path(r'hello/<int:1>/', lambda r: None)

    def test_non_identifier_parameter_name_causes_exception(self):
        msg = (
            "URL route 'b/<int:book.id>/' uses parameter name 'book.id' which "
            "isn't a valid Python identifier."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            path(r'b/<int:book.id>/', lambda r: None)

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

    def test_resolve_type_error_propagates(self):
        @DynamicConverter.register_to_python
        def raises_type_error(value):
            raise TypeError('This type error propagates.')
        with self.assertRaisesMessage(TypeError, 'This type error propagates.'):
            resolve('/dynamic/abc/')

    def test_reverse_value_error_means_no_match(self):
        @DynamicConverter.register_to_url
        def raises_value_error(value):
            raise ValueError
        with self.assertRaises(NoReverseMatch):
            reverse('dynamic', kwargs={'value': object()})

    def test_reverse_type_error_propagates(self):
        @DynamicConverter.register_to_url
        def raises_type_error(value):
            raise TypeError('This type error propagates.')
        with self.assertRaisesMessage(TypeError, 'This type error propagates.'):
            reverse('dynamic', kwargs={'value': object()})


class DeprecationTests(SimpleTestCase):
    def test_url_warning(self):
        msg = (
            'django.conf.urls.url() is deprecated in favor of '
            'django.urls.re_path().'
        )
        with self.assertRaisesMessage(RemovedInDjango40Warning, msg):
            conf_url(r'^regex/(?P<pk>[0-9]+)/$', empty_view, name='regex')
