from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.middleware.locale import LocaleMiddleware
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings
from django.test.client import RequestFactory
from django.test.utils import override_script_prefix
from django.urls import clear_url_caches, resolve, reverse, translate_url
from django.utils import translation


class PermanentRedirectLocaleMiddleWare(LocaleMiddleware):
    response_redirect_class = HttpResponsePermanentRedirect


@override_settings(
    USE_I18N=True,
    LOCALE_PATHS=[
        Path(__file__).parent / "locale",
    ],
    LANGUAGE_CODE="en-us",
    LANGUAGES=[
        ("nl", "Dutch"),
        ("en", "English"),
        ("pt-br", "Brazilian Portuguese"),
    ],
    MIDDLEWARE=[
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
    ],
    ROOT_URLCONF="i18n.patterns.urls.default",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [Path(__file__).parent / "templates"],
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.i18n",
                ],
            },
        }
    ],
)
class URLTestCaseBase(SimpleTestCase):
    """
    TestCase base-class for the URL tests.
    """

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
        with translation.override("en"):
            self.assertEqual(reverse("not-prefixed"), "/not-prefixed/")
            self.assertEqual(
                reverse("not-prefixed-included-url"), "/not-prefixed-include/foo/"
            )
        with translation.override("nl"):
            self.assertEqual(reverse("not-prefixed"), "/not-prefixed/")
            self.assertEqual(
                reverse("not-prefixed-included-url"), "/not-prefixed-include/foo/"
            )

    def test_prefixed(self):
        with translation.override("en"):
            self.assertEqual(reverse("prefixed"), "/en/prefixed/")
        with translation.override("nl"):
            self.assertEqual(reverse("prefixed"), "/nl/prefixed/")
        with translation.override(None):
            self.assertEqual(
                reverse("prefixed"), "/%s/prefixed/" % settings.LANGUAGE_CODE
            )

    @override_settings(ROOT_URLCONF="i18n.patterns.urls.wrong")
    def test_invalid_prefix_use(self):
        msg = "Using i18n_patterns in an included URLconf is not allowed."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            reverse("account:register")


@override_settings(ROOT_URLCONF="i18n.patterns.urls.disabled")
class URLDisabledTests(URLTestCaseBase):
    @override_settings(USE_I18N=False)
    def test_prefixed_i18n_disabled(self):
        with translation.override("en"):
            self.assertEqual(reverse("prefixed"), "/prefixed/")
        with translation.override("nl"):
            self.assertEqual(reverse("prefixed"), "/prefixed/")


class RequestURLConfTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="i18n.patterns.urls.path_unused")
    def test_request_urlconf_considered(self):
        request = RequestFactory().get("/nl/")
        request.urlconf = "i18n.patterns.urls.default"
        middleware = LocaleMiddleware(lambda req: HttpResponse())
        with translation.override("nl"):
            middleware.process_request(request)
        self.assertEqual(request.LANGUAGE_CODE, "nl")


@override_settings(ROOT_URLCONF="i18n.patterns.urls.path_unused")
class PathUnusedTests(URLTestCaseBase):
    """
    If no i18n_patterns is used in root URLconfs, then no language activation
    activation happens based on url prefix.
    """

    def test_no_lang_activate(self):
        response = self.client.get("/nl/foo/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "en")
        self.assertEqual(response.context["LANGUAGE_CODE"], "en")


class URLTranslationTests(URLTestCaseBase):
    """
    Tests if the pattern-strings are translated correctly (within the
    `i18n_patterns` and the normal `patterns` function).
    """

    def test_no_prefix_translated(self):
        with translation.override("en"):
            self.assertEqual(reverse("no-prefix-translated"), "/translated/")
            self.assertEqual(
                reverse("no-prefix-translated-slug", kwargs={"slug": "yeah"}),
                "/translated/yeah/",
            )

        with translation.override("nl"):
            self.assertEqual(reverse("no-prefix-translated"), "/vertaald/")
            self.assertEqual(
                reverse("no-prefix-translated-slug", kwargs={"slug": "yeah"}),
                "/vertaald/yeah/",
            )

        with translation.override("pt-br"):
            self.assertEqual(reverse("no-prefix-translated"), "/traduzidos/")
            self.assertEqual(
                reverse("no-prefix-translated-slug", kwargs={"slug": "yeah"}),
                "/traduzidos/yeah/",
            )

    def test_users_url(self):
        with translation.override("en"):
            self.assertEqual(reverse("users"), "/en/users/")

        with translation.override("nl"):
            self.assertEqual(reverse("users"), "/nl/gebruikers/")
            self.assertEqual(reverse("prefixed_xml"), "/nl/prefixed.xml")

        with translation.override("pt-br"):
            self.assertEqual(reverse("users"), "/pt-br/usuarios/")

    def test_translate_url_utility(self):
        with translation.override("en"):
            self.assertEqual(
                translate_url("/en/nonexistent/", "nl"), "/en/nonexistent/"
            )
            self.assertEqual(translate_url("/en/users/", "nl"), "/nl/gebruikers/")
            # Namespaced URL
            self.assertEqual(
                translate_url("/en/account/register/", "nl"), "/nl/profiel/registreren/"
            )
            # path() URL pattern
            self.assertEqual(
                translate_url("/en/account/register-as-path/", "nl"),
                "/nl/profiel/registreren-als-pad/",
            )
            self.assertEqual(translation.get_language(), "en")
            # URL with parameters.
            self.assertEqual(
                translate_url("/en/with-arguments/regular-argument/", "nl"),
                "/nl/with-arguments/regular-argument/",
            )
            self.assertEqual(
                translate_url(
                    "/en/with-arguments/regular-argument/optional.html", "nl"
                ),
                "/nl/with-arguments/regular-argument/optional.html",
            )

        with translation.override("nl"):
            self.assertEqual(translate_url("/nl/gebruikers/", "en"), "/en/users/")
            self.assertEqual(translation.get_language(), "nl")

    def test_reverse_translated_with_captured_kwargs(self):
        with translation.override("en"):
            match = resolve("/translated/apo/")
        # Links to the same page in other languages.
        tests = [
            ("nl", "/vertaald/apo/"),
            ("pt-br", "/traduzidos/apo/"),
        ]
        for lang, expected_link in tests:
            with translation.override(lang):
                self.assertEqual(
                    reverse(
                        match.url_name, args=match.args, kwargs=match.captured_kwargs
                    ),
                    expected_link,
                )

    def test_locale_not_interepreted_as_regex(self):
        with translation.override("e("):
            # Would previously error:
            # re.error: missing ), unterminated subpattern at position 1
            reverse("users")


class URLNamespaceTests(URLTestCaseBase):
    """
    Tests if the translations are still working within namespaces.
    """

    def test_account_register(self):
        with translation.override("en"):
            self.assertEqual(reverse("account:register"), "/en/account/register/")
            self.assertEqual(
                reverse("account:register-as-path"), "/en/account/register-as-path/"
            )

        with translation.override("nl"):
            self.assertEqual(reverse("account:register"), "/nl/profiel/registreren/")
            self.assertEqual(
                reverse("account:register-as-path"), "/nl/profiel/registreren-als-pad/"
            )


class URLRedirectTests(URLTestCaseBase):
    """
    Tests if the user gets redirected to the right URL when there is no
    language-prefix in the request URL.
    """

    def test_no_prefix_response(self):
        response = self.client.get("/not-prefixed/")
        self.assertEqual(response.status_code, 200)

    def test_en_redirect(self):
        response = self.client.get("/account/register/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertRedirects(response, "/en/account/register/")

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)

    def test_en_redirect_wrong_url(self):
        response = self.client.get("/profiel/registreren/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 404)

    def test_nl_redirect(self):
        response = self.client.get("/profiel/registreren/", HTTP_ACCEPT_LANGUAGE="nl")
        self.assertRedirects(response, "/nl/profiel/registreren/")

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)

    def test_nl_redirect_wrong_url(self):
        response = self.client.get("/account/register/", HTTP_ACCEPT_LANGUAGE="nl")
        self.assertEqual(response.status_code, 404)

    def test_pt_br_redirect(self):
        response = self.client.get("/conta/registre-se/", HTTP_ACCEPT_LANGUAGE="pt-br")
        self.assertRedirects(response, "/pt-br/conta/registre-se/")

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)

    def test_pl_pl_redirect(self):
        # language from outside of the supported LANGUAGES list
        response = self.client.get("/account/register/", HTTP_ACCEPT_LANGUAGE="pl-pl")
        self.assertRedirects(response, "/en/account/register/")

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)

    @override_settings(
        MIDDLEWARE=[
            "i18n.patterns.tests.PermanentRedirectLocaleMiddleWare",
            "django.middleware.common.CommonMiddleware",
        ],
    )
    def test_custom_redirect_class(self):
        response = self.client.get("/account/register/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertRedirects(response, "/en/account/register/", 301)


class URLVaryAcceptLanguageTests(URLTestCaseBase):
    """
    'Accept-Language' is not added to the Vary header when using prefixed URLs.
    """

    def test_no_prefix_response(self):
        response = self.client.get("/not-prefixed/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Vary"), "Accept-Language")

    def test_en_redirect(self):
        """
        The redirect to a prefixed URL depends on 'Accept-Language' and
        'Cookie', but once prefixed no header is set.
        """
        response = self.client.get("/account/register/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertRedirects(response, "/en/account/register/")
        self.assertEqual(response.get("Vary"), "Accept-Language, Cookie")

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get("Vary"))


class URLRedirectWithoutTrailingSlashTests(URLTestCaseBase):
    """
    Tests the redirect when the requested URL doesn't end with a slash
    (`settings.APPEND_SLASH=True`).
    """

    def test_not_prefixed_redirect(self):
        response = self.client.get("/not-prefixed", HTTP_ACCEPT_LANGUAGE="en")
        self.assertRedirects(response, "/not-prefixed/", 301)

    def test_en_redirect(self):
        response = self.client.get(
            "/account/register", HTTP_ACCEPT_LANGUAGE="en", follow=True
        )
        # We only want one redirect, bypassing CommonMiddleware
        self.assertEqual(response.redirect_chain, [("/en/account/register/", 302)])
        self.assertRedirects(response, "/en/account/register/", 302)

        response = self.client.get(
            "/prefixed.xml", HTTP_ACCEPT_LANGUAGE="en", follow=True
        )
        self.assertRedirects(response, "/en/prefixed.xml", 302)


class URLRedirectWithoutTrailingSlashSettingTests(URLTestCaseBase):
    """
    Tests the redirect when the requested URL doesn't end with a slash
    (`settings.APPEND_SLASH=False`).
    """

    @override_settings(APPEND_SLASH=False)
    def test_not_prefixed_redirect(self):
        response = self.client.get("/not-prefixed", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 404)

    @override_settings(APPEND_SLASH=False)
    def test_en_redirect(self):
        response = self.client.get(
            "/account/register-without-slash", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertRedirects(response, "/en/account/register-without-slash", 302)

        response = self.client.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)


class URLResponseTests(URLTestCaseBase):
    """Tests if the response has the correct language code."""

    def test_not_prefixed_with_prefix(self):
        response = self.client.get("/en/not-prefixed/")
        self.assertEqual(response.status_code, 404)

    def test_en_url(self):
        response = self.client.get("/en/account/register/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "en")
        self.assertEqual(response.context["LANGUAGE_CODE"], "en")

    def test_nl_url(self):
        response = self.client.get("/nl/profiel/registreren/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "nl")
        self.assertEqual(response.context["LANGUAGE_CODE"], "nl")

    def test_wrong_en_prefix(self):
        response = self.client.get("/en/profiel/registreren/")
        self.assertEqual(response.status_code, 404)

    def test_wrong_nl_prefix(self):
        response = self.client.get("/nl/account/register/")
        self.assertEqual(response.status_code, 404)

    def test_pt_br_url(self):
        response = self.client.get("/pt-br/conta/registre-se/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "pt-br")
        self.assertEqual(response.context["LANGUAGE_CODE"], "pt-br")

    def test_en_path(self):
        response = self.client.get("/en/account/register-as-path/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "en")
        self.assertEqual(response.context["LANGUAGE_CODE"], "en")

    def test_nl_path(self):
        response = self.client.get("/nl/profiel/registreren-als-pad/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-language"], "nl")
        self.assertEqual(response.context["LANGUAGE_CODE"], "nl")


class URLRedirectWithScriptAliasTests(URLTestCaseBase):
    """
    #21579 - LocaleMiddleware should respect the script prefix.
    """

    def test_language_prefix_with_script_prefix(self):
        prefix = "/script_prefix"
        with override_script_prefix(prefix):
            response = self.client.get(
                "/prefixed/", HTTP_ACCEPT_LANGUAGE="en", SCRIPT_NAME=prefix
            )
            self.assertRedirects(
                response, "%s/en/prefixed/" % prefix, target_status_code=404
            )


class URLTagTests(URLTestCaseBase):
    """
    Test if the language tag works.
    """

    def test_strings_only(self):
        t = Template(
            """{% load i18n %}
            {% language 'nl' %}{% url 'no-prefix-translated' %}{% endlanguage %}
            {% language 'pt-br' %}{% url 'no-prefix-translated' %}{% endlanguage %}"""
        )
        self.assertEqual(
            t.render(Context({})).strip().split(), ["/vertaald/", "/traduzidos/"]
        )

    def test_context(self):
        ctx = Context({"lang1": "nl", "lang2": "pt-br"})
        tpl = Template(
            """{% load i18n %}
            {% language lang1 %}{% url 'no-prefix-translated' %}{% endlanguage %}
            {% language lang2 %}{% url 'no-prefix-translated' %}{% endlanguage %}"""
        )
        self.assertEqual(
            tpl.render(ctx).strip().split(), ["/vertaald/", "/traduzidos/"]
        )

    def test_args(self):
        tpl = Template(
            """
            {% load i18n %}
            {% language 'nl' %}
            {% url 'no-prefix-translated-slug' 'apo' %}{% endlanguage %}
            {% language 'pt-br' %}
            {% url 'no-prefix-translated-slug' 'apo' %}{% endlanguage %}
            """
        )
        self.assertEqual(
            tpl.render(Context({})).strip().split(),
            ["/vertaald/apo/", "/traduzidos/apo/"],
        )

    def test_kwargs(self):
        tpl = Template(
            """
            {% load i18n %}
            {% language 'nl'  %}
            {% url 'no-prefix-translated-slug' slug='apo' %}{% endlanguage %}
            {% language 'pt-br' %}
            {% url 'no-prefix-translated-slug' slug='apo' %}{% endlanguage %}
            """
        )
        self.assertEqual(
            tpl.render(Context({})).strip().split(),
            ["/vertaald/apo/", "/traduzidos/apo/"],
        )
