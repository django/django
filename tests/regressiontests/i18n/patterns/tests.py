import os
import warnings

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, clear_url_caches
from django.test import TestCase
from django.test.utils import override_settings
from django.template import Template, Context
from django.utils import translation


@override_settings(
    USE_I18N=True,
    LOCALE_PATHS=(
        os.path.join(os.path.dirname(__file__), 'locale'),
    ),
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(__file__), 'templates'),
    ),
    LANGUAGE_CODE='en',
    LANGUAGES=(
        ('nl', 'Dutch'),
        ('en', 'English'),
        ('pt-br', 'Brazilian Portuguese'),
    ),
    MIDDLEWARE_CLASSES=(
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
    ),
)
class URLTestCaseBase(TestCase):
    """
    TestCase base-class for the URL tests.
    """
    urls = 'regressiontests.i18n.patterns.urls.default'

    def setUp(self):
        # Make sure the cache is empty before we are doing our tests.
        clear_url_caches()

    def tearDown(self):
        # Make sure we will leave an empty cache for other testcases.
        clear_url_caches()


class URLPrefixTests(URLTestCaseBase):
    """
    Tests if the `i18n_patterns` is adding the prefix correctly.
    """
    def test_not_prefixed(self):
        with translation.override('en'):
            self.assertEqual(reverse('not-prefixed'), '/not-prefixed/')
        with translation.override('nl'):
            self.assertEqual(reverse('not-prefixed'), '/not-prefixed/')

    def test_prefixed(self):
        with translation.override('en'):
            self.assertEqual(reverse('prefixed'), '/en/prefixed/')
        with translation.override('nl'):
            self.assertEqual(reverse('prefixed'), '/nl/prefixed/')

    @override_settings(ROOT_URLCONF='regressiontests.i18n.patterns.urls.wrong')
    def test_invalid_prefix_use(self):
        self.assertRaises(ImproperlyConfigured, lambda: reverse('account:register'))


class URLDisabledTests(URLTestCaseBase):
    urls = 'regressiontests.i18n.patterns.urls.disabled'

    @override_settings(USE_I18N=False)
    def test_prefixed_i18n_disabled(self):
        with translation.override('en'):
            self.assertEqual(reverse('prefixed'), '/prefixed/')
        with translation.override('nl'):
            self.assertEqual(reverse('prefixed'), '/prefixed/')


class PathUnusedTests(URLTestCaseBase):
    """
    Check that if no i18n_patterns is used in root urlconfs, then no
    language activation happens based on url prefix.
    """
    urls = 'regressiontests.i18n.patterns.urls.path_unused'

    def test_no_lang_activate(self):
        response = self.client.get('/nl/foo/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-language'], 'en')
        self.assertEqual(response.context['LANGUAGE_CODE'], 'en')


class URLTranslationTests(URLTestCaseBase):
    """
    Tests if the pattern-strings are translated correctly (within the
    `i18n_patterns` and the normal `patterns` function).
    """
    def test_no_prefix_translated(self):
        with translation.override('en'):
            self.assertEqual(reverse('no-prefix-translated'), '/translated/')
            self.assertEqual(reverse('no-prefix-translated-slug', kwargs={'slug': 'yeah'}), '/translated/yeah/')

        with translation.override('nl'):
            self.assertEqual(reverse('no-prefix-translated'), '/vertaald/')
            self.assertEqual(reverse('no-prefix-translated-slug', kwargs={'slug': 'yeah'}), '/vertaald/yeah/')

        with translation.override('pt-br'):
            self.assertEqual(reverse('no-prefix-translated'), '/traduzidos/')
            self.assertEqual(reverse('no-prefix-translated-slug', kwargs={'slug': 'yeah'}), '/traduzidos/yeah/')

    def test_users_url(self):
        with translation.override('en'):
            self.assertEqual(reverse('users'), '/en/users/')

        with translation.override('nl'):
            self.assertEqual(reverse('users'), '/nl/gebruikers/')

        with translation.override('pt-br'):
            self.assertEqual(reverse('users'), '/pt-br/usuarios/')


class URLNamespaceTests(URLTestCaseBase):
    """
    Tests if the translations are still working within namespaces.
    """
    def test_account_register(self):
        with translation.override('en'):
            self.assertEqual(reverse('account:register'), '/en/account/register/')

        with translation.override('nl'):
            self.assertEqual(reverse('account:register'), '/nl/profiel/registeren/')


class URLRedirectTests(URLTestCaseBase):
    """
    Tests if the user gets redirected to the right URL when there is no
    language-prefix in the request URL.
    """
    def test_no_prefix_response(self):
        response = self.client.get('/not-prefixed/')
        self.assertEqual(response.status_code, 200)

    def test_en_redirect(self):
        response = self.client.get('/account/register/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, '/en/account/register/')

        response = self.client.get(response['location'])
        self.assertEqual(response.status_code, 200)

    def test_en_redirect_wrong_url(self):
        response = self.client.get('/profiel/registeren/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(response.status_code, 404)

    def test_nl_redirect(self):
        response = self.client.get('/profiel/registeren/', HTTP_ACCEPT_LANGUAGE='nl')
        self.assertRedirects(response, '/nl/profiel/registeren/')

        response = self.client.get(response['location'])
        self.assertEqual(response.status_code, 200)

    def test_nl_redirect_wrong_url(self):
        response = self.client.get('/account/register/', HTTP_ACCEPT_LANGUAGE='nl')
        self.assertEqual(response.status_code, 404)

    def test_pt_br_redirect(self):
        response = self.client.get('/conta/registre-se/', HTTP_ACCEPT_LANGUAGE='pt-br')
        self.assertRedirects(response, '/pt-br/conta/registre-se/')

        response = self.client.get(response['location'])
        self.assertEqual(response.status_code, 200)


class URLRedirectWithoutTrailingSlashTests(URLTestCaseBase):
    """
    Tests the redirect when the requested URL doesn't end with a slash
    (`settings.APPEND_SLASH=True`).
    """
    def test_not_prefixed_redirect(self):
        response = self.client.get('/not-prefixed', HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, '/not-prefixed/', 301)

    def test_en_redirect(self):
        response = self.client.get('/account/register', HTTP_ACCEPT_LANGUAGE='en', follow=True)
        # target status code of 301 because of CommonMiddleware redirecting
        self.assertIn(('http://testserver/en/account/register/', 301), response.redirect_chain)
        self.assertRedirects(response, '/en/account/register/', 302)


class URLRedirectWithoutTrailingSlashSettingTests(URLTestCaseBase):
    """
    Tests the redirect when the requested URL doesn't end with a slash
    (`settings.APPEND_SLASH=False`).
    """
    @override_settings(APPEND_SLASH=False)
    def test_not_prefixed_redirect(self):
        response = self.client.get('/not-prefixed', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(response.status_code, 404)

    @override_settings(APPEND_SLASH=False)
    def test_en_redirect(self):
        response = self.client.get('/account/register-without-slash', HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, '/en/account/register-without-slash', 302)

        response = self.client.get(response['location'])
        self.assertEqual(response.status_code, 200)


class URLResponseTests(URLTestCaseBase):
    """
    Tests if the response has the right language-code.
    """
    def test_not_prefixed_with_prefix(self):
        response = self.client.get('/en/not-prefixed/')
        self.assertEqual(response.status_code, 404)

    def test_en_url(self):
        response = self.client.get('/en/account/register/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-language'], 'en')
        self.assertEqual(response.context['LANGUAGE_CODE'], 'en')

    def test_nl_url(self):
        response = self.client.get('/nl/profiel/registeren/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-language'], 'nl')
        self.assertEqual(response.context['LANGUAGE_CODE'], 'nl')

    def test_wrong_en_prefix(self):
        response = self.client.get('/en/profiel/registeren/')
        self.assertEqual(response.status_code, 404)

    def test_wrong_nl_prefix(self):
        response = self.client.get('/nl/account/register/')
        self.assertEqual(response.status_code, 404)

    def test_pt_br_url(self):
        response = self.client.get('/pt-br/conta/registre-se/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-language'], 'pt-br')
        self.assertEqual(response.context['LANGUAGE_CODE'], 'pt-br')


class URLTagTests(URLTestCaseBase):
    """
    Test if the language tag works.
    """
    def test_strings_only(self):
        t = Template("""{% load i18n %}
            {% language 'nl' %}{% url 'no-prefix-translated' %}{% endlanguage %}
            {% language 'pt-br' %}{% url 'no-prefix-translated' %}{% endlanguage %}""")
        self.assertEqual(t.render(Context({})).strip().split(),
                         [u'/vertaald/', u'/traduzidos/'])

    def test_context(self):
        ctx = Context({'lang1':'nl', 'lang2':'pt-br'})
        tpl = Template("""{% load i18n %}
            {% language lang1 %}{% url 'no-prefix-translated' %}{% endlanguage %}
            {% language lang2 %}{% url 'no-prefix-translated' %}{% endlanguage %}""")
        self.assertEqual(tpl.render(ctx).strip().split(),
                         [u'/vertaald/', u'/traduzidos/'])

    def test_args(self):
        tpl = Template("""{% load i18n %}
            {% language 'nl' %}{% url 'no-prefix-translated-slug' 'apo' %}{% endlanguage %}
            {% language 'pt-br' %}{% url 'no-prefix-translated-slug' 'apo' %}{% endlanguage %}""")
        self.assertEqual(tpl.render(Context({})).strip().split(),
                         [u'/vertaald/apo/', u'/traduzidos/apo/'])

    def test_kwargs(self):
        tpl = Template("""{% load i18n %}
            {% language 'nl'  %}{% url 'no-prefix-translated-slug' slug='apo' %}{% endlanguage %}
            {% language 'pt-br' %}{% url 'no-prefix-translated-slug' slug='apo' %}{% endlanguage %}""")
        self.assertEqual(tpl.render(Context({})).strip().split(),
                         [u'/vertaald/apo/', u'/traduzidos/apo/'])
