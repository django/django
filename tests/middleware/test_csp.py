from io import BytesIO

from playwright_tests import PlaywrightTestCase
from utils_tests.test_csp import basic_config, basic_policy

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.middleware.csp import ContentSecurityPolicyMiddleware
from django.template import Context, Template
from django.template.context_processors import csp
from django.test import RequestFactory, SimpleTestCase
from django.test.utils import modify_settings, override_settings
from django.utils.csp import CSP

from .views import csp_reports

nonce_config = {"default-src": [CSP.SELF, CSP.NONCE]}
# Each setting the middleware reads, paired with the header it produces.
csp_settings = [
    ("SECURE_CSP", CSP.HEADER_ENFORCE),
    ("SECURE_CSP_REPORT_ONLY", CSP.HEADER_REPORT_ONLY),
]


class CSPMiddlewareNonceCachingAllowed(ContentSecurityPolicyMiddleware):
    nonce_caching_allowed = True


@override_settings(
    MIDDLEWARE=["django.middleware.csp.ContentSecurityPolicyMiddleware"],
    ROOT_URLCONF="middleware.urls",
)
class CSPMiddlewareTest(SimpleTestCase):
    @override_settings(SECURE_CSP=None, SECURE_CSP_REPORT_ONLY=None)
    def test_csp_defaults_off(self):
        response = self.client.get("/csp-base/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP=basic_config, SECURE_CSP_REPORT_ONLY=None)
    def test_csp_basic(self):
        """
        With SECURE_CSP set to a valid value, the middleware adds a
        "Content-Security-Policy" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP={"default-src": [CSP.SELF, CSP.NONCE]})
    def test_csp_basic_with_nonce(self):
        """
        Test the nonce is added to the header and matches what is in the view.
        """
        response = self.client.get("/csp-nonce/")
        nonce = response.text
        self.assertTrue(nonce)
        self.assertEqual(
            response[CSP.HEADER_ENFORCE], f"default-src 'self' 'nonce-{nonce}'"
        )

    def test_csp_basic_with_nonce_but_unused(self):
        """
        Test if `request.csp_nonce` is never accessed, it is not added to the
        header, and caching is left untouched.
        """
        for setting, header in csp_settings:
            with (
                self.subTest(setting=setting),
                self.settings(**{setting: nonce_config}),
            ):
                response = self.client.get("/csp-base/")
                nonce = response.text
                self.assertIsNotNone(nonce)
                self.assertEqual(response[header], basic_policy)
                self.assertNotIn("Cache-Control", response)

    def test_csp_nonce_overrides_explicit_public_cache_control(self):
        """A rendered nonce overrides an explicit public Cache-Control."""
        for setting, _ in csp_settings:
            with (
                self.subTest(setting=setting),
                self.settings(**{setting: nonce_config}),
            ):
                response = self.client.get("/csp-nonce-public/")
                self.assertTrue(response.text)
                self.assertIn("private", response["Cache-Control"])
                self.assertNotIn("public", response["Cache-Control"])

    def test_csp_nonce_used_but_not_in_policy(self):
        """
        A nonce that isn't in any CSP header can't be replayed, so caching is
        left untouched.
        """
        for setting, header in csp_settings:
            with (
                self.subTest(setting=setting),
                self.settings(**{setting: basic_config}),
            ):
                response = self.client.get("/csp-nonce/")
                self.assertTrue(response.text)
                self.assertEqual(response[header], basic_policy)
                self.assertNotIn("Cache-Control", response)

    @override_settings(
        MIDDLEWARE=["middleware.test_csp.CSPMiddlewareNonceCachingAllowed"],
    )
    def test_csp_nonce_caching_allowed(self):
        """A project that opts out shouldn't get Cache-Control forced on it."""
        for setting, _ in csp_settings:
            with (
                self.subTest(setting=setting),
                self.settings(**{setting: nonce_config}),
            ):
                response = self.client.get("/csp-nonce/")
                self.assertTrue(response.text)
                self.assertNotIn("Cache-Control", response)

    @override_settings(
        MIDDLEWARE=[
            "django.middleware.cache.UpdateCacheMiddleware",
            "django.middleware.csp.ContentSecurityPolicyMiddleware",
            "django.middleware.cache.FetchFromCacheMiddleware",
        ],
    )
    def test_csp_nonce_not_reused_across_cached_responses(self):
        """A cached response must not replay one visitor's nonce to another."""
        cache = caches[DEFAULT_CACHE_ALIAS]
        self.addCleanup(cache.clear)
        for setting, _ in csp_settings:
            with (
                self.subTest(setting=setting),
                self.settings(**{setting: nonce_config}),
            ):
                cache.clear()
                first_nonce = self.client.get("/csp-nonce/").text
                second_nonce = self.client.get("/csp-nonce/").text
                self.assertNotEqual(first_nonce, second_nonce)

    @override_settings(SECURE_CSP={"script-src": [CSP.NONCE]})
    def test_csp_nonce_only_directive_emits_none(self):
        """
        A directive whose only source is CSP.NONCE is emitted as 'none' when
        the nonce is never used, so the policy fails closed.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], "script-src 'none'")

    @override_settings(SECURE_CSP={"script-src": CSP.NONCE})
    def test_csp_nonce_only_directive_as_string_emits_none(self):
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], "script-src 'none'")

    @override_settings(
        SECURE_CSP=None, SECURE_CSP_REPORT_ONLY={"script-src": [CSP.NONCE]}
    )
    def test_csp_report_only_nonce_only_directive(self):
        response = self.client.get("/csp-base/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], "script-src 'none'")

    @override_settings(
        SECURE_CSP={
            "default-src": [CSP.SELF],
            "script-src": [CSP.SELF, CSP.NONCE],
        }
    )
    def test_csp_mixed_directive_omits_unused_nonce(self):
        """
        Directives with sources other than CSP.NONCE still have an unused
        nonce sentinel removed without emitting 'none'.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(
            response[CSP.HEADER_ENFORCE], "default-src 'self'; script-src 'self'"
        )

    @override_settings(SECURE_CSP=None, SECURE_CSP_REPORT_ONLY=basic_config)
    def test_csp_report_only_basic(self):
        """
        With SECURE_CSP_REPORT_ONLY set to a valid value, the middleware adds a
        "Content-Security-Policy-Report-Only" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)
        self.assertNotIn(CSP.HEADER_ENFORCE, response)

    @override_settings(
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_both(self):
        """
        If both SECURE_CSP and SECURE_CSP_REPORT_ONLY are set, the middleware
        adds both headers to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)

    @override_settings(
        DEBUG=True,
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_404_debug_view(self):
        """
        Test that the CSP headers are not added to the debug view.
        """
        response = self.client.get("/csp-404/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(
        DEBUG=True,
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_500_debug_view(self):
        """
        Test that the CSP headers are not added to the debug view.
        """
        with self.assertLogs("django.request", "WARNING"):
            response = self.client.get("/csp-500/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)


@override_settings(
    MIDDLEWARE=["django.middleware.csp.ContentSecurityPolicyMiddleware"],
    ROOT_URLCONF="middleware.urls",
    SECURE_CSP=basic_config,
    SECURE_CSP_REPORT_ONLY=basic_config,
)
class CSPMiddlewareWithDecoratedViewsTest(SimpleTestCase):
    def test_no_decorators(self):
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)

    def test_csp_disabled_enforced(self):
        """
        `csp_override({})` only disables the enforced CSP header.
        """
        response = self.client.get("/csp-disabled-enforced/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)

    def test_csp_report_only_disabled(self):
        """
        `csp_report_only_override({})` only disables the report-only header.
        """
        response = self.client.get("/csp-disabled-report-only/")
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)

    def test_csp_disabled_both(self):
        """
        Using both CSP decorators with empty mappings will clear both headers.
        """
        response = self.client.get("/csp-disabled-both/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    def test_csp_override_enforced(self):
        """
        `csp_override` only overrides the enforced header.
        """
        response = self.client.get("/csp-override-enforced/")
        self.assertEqual(
            response[CSP.HEADER_ENFORCE], "default-src 'self'; img-src 'self' data:"
        )
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)

    def test_csp_report_only_override(self):
        """
        `csp_report_only_override` only overrides the report-only header.
        """
        response = self.client.get("/csp-override-report-only/")
        self.assertEqual(
            response[CSP.HEADER_REPORT_ONLY], "default-src 'self'; img-src 'self' data:"
        )
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)

    def test_csp_override_both_decorator(self):
        """
        Using both CSP decorators overrides both CSP Django settings.
        """
        response = self.client.get("/csp-override-both/")
        self.assertEqual(
            response[CSP.HEADER_ENFORCE], "default-src 'self'; img-src 'self' data:"
        )
        self.assertEqual(
            response[CSP.HEADER_REPORT_ONLY], "default-src 'self'; img-src 'self' data:"
        )


class CSPStreamingTests(SimpleTestCase):
    def test_nonce_generated_during_streaming_is_in_header(self):
        request = RequestFactory().get("/")
        template = Template('<script nonce="{{ csp_nonce }}"></script>')

        def view(request):
            def content():
                yield template.render(Context(csp(request)))

            return StreamingHttpResponse(content())

        csp_setting = {
            "default-src": [CSP.SELF],
            "script-src": [CSP.NONCE],
        }
        for csp_header, setting in [
            (CSP.HEADER_ENFORCE, {"SECURE_CSP": csp_setting}),
            (CSP.HEADER_REPORT_ONLY, {"SECURE_CSP_REPORT_ONLY": csp_setting}),
        ]:
            with self.subTest(csp_header=csp_header):
                with override_settings(**setting):
                    response = ContentSecurityPolicyMiddleware(view)(request)
                    body = b"".join(response.streaming_content).decode()
                    nonce = body.split('nonce="', 1)[1].split('"', 1)[0]
                    self.assertTrue(nonce)
                    self.assertIn(f"'nonce-{nonce}'", response[csp_header])

    @override_settings(
        SECURE_CSP={
            "style-src": [CSP.SELF, CSP.UNSAFE_INLINE, CSP.NONCE],
        }
    )
    def test_unused_nonce_with_unsafe_inline(self):
        body = b'<div style="color: red">Hello</div>'
        responses = (
            HttpResponse(body),
            StreamingHttpResponse(iter([body])),
            FileResponse(BytesIO(body), content_type="text/html"),
        )

        for response in responses:
            with self.subTest(response=type(response).__name__):
                request = RequestFactory().get("/")
                try:
                    response = ContentSecurityPolicyMiddleware(
                        lambda request: response
                    )(request)
                    header = response[CSP.HEADER_ENFORCE]
                    self.assertIn("'unsafe-inline'", header)
                    if response.streaming:
                        self.assertRegex(
                            header,
                            r"^style-src 'self' 'unsafe-inline' 'nonce-[^']+'$",
                        )
                    else:
                        self.assertEqual(header, "style-src 'self' 'unsafe-inline'")
                finally:
                    response.close()


@override_settings(
    ROOT_URLCONF="middleware.urls",
)
@modify_settings(
    MIDDLEWARE={"append": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
)
class CSPPlaywrightTestCase(PlaywrightTestCase, StaticLiveServerTestCase):
    available_apps = ["middleware"]

    def setUp(self):
        self.addCleanup(csp_reports.clear)
        super().setUp()

    def test_reports_are_generated(self):
        url = self.live_server_url + "/csp-failure/"
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")
        reports = sorted(
            (r["csp-report"]["document-uri"], r["csp-report"]["violated-directive"])
            for r in csp_reports
        )
        self.assertEqual(reports, [(url, "style-src-elem")])
