from django.http import HttpResponse
from django.middleware.constants import csp
from django.test import RequestFactory, SimpleTestCase
from django.test.utils import override_settings


class SecurityMiddlewareTest(SimpleTestCase):
    def middleware(self, *args, **kwargs):
        from django.middleware.security import SecurityMiddleware

        return SecurityMiddleware(self.response(*args, **kwargs))

    @property
    def secure_request_kwargs(self):
        return {"wsgi.url_scheme": "https"}

    def response(self, *args, headers=None, **kwargs):
        def get_response(req):
            response = HttpResponse(*args, **kwargs)
            if headers:
                for k, v in headers.items():
                    response.headers[k] = v
            return response

        return get_response

    def process_response(self, *args, secure=False, request=None, **kwargs):
        request_kwargs = {}
        if secure:
            request_kwargs.update(self.secure_request_kwargs)
        if request is None:
            request = self.request.get("/some/url", **request_kwargs)
        ret = self.middleware(*args, **kwargs).process_request(request)
        if ret:
            return ret
        return self.middleware(*args, **kwargs)(request)

    request = RequestFactory()

    def process_request(self, method, *args, secure=False, **kwargs):
        if secure:
            kwargs.update(self.secure_request_kwargs)
        req = getattr(self.request, method.lower())(*args, **kwargs)
        return self.middleware().process_request(req)

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_on(self):
        """
        With SECURE_HSTS_SECONDS=3600, the middleware adds
        "Strict-Transport-Security: max-age=3600" to the response.
        """
        self.assertEqual(
            self.process_response(secure=True).headers["Strict-Transport-Security"],
            "max-age=3600",
        )

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_already_present(self):
        """
        The middleware will not override a "Strict-Transport-Security" header
        already present in the response.
        """
        response = self.process_response(
            secure=True, headers={"Strict-Transport-Security": "max-age=7200"}
        )
        self.assertEqual(response.headers["Strict-Transport-Security"], "max-age=7200")

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_only_if_secure(self):
        """
        The "Strict-Transport-Security" header is not added to responses going
        over an insecure connection.
        """
        self.assertNotIn(
            "Strict-Transport-Security",
            self.process_response(secure=False).headers,
        )

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_sts_off(self):
        """
        With SECURE_HSTS_SECONDS=0, the middleware does not add a
        "Strict-Transport-Security" header to the response.
        """
        self.assertNotIn(
            "Strict-Transport-Security",
            self.process_response(secure=True).headers,
        )

    @override_settings(SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_sts_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        True, the middleware adds a "Strict-Transport-Security" header with the
        "includeSubDomains" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=600; includeSubDomains",
        )

    @override_settings(SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_sts_no_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "Strict-Transport-Security" header without
        the "includeSubDomains" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response.headers["Strict-Transport-Security"], "max-age=600")

    @override_settings(SECURE_HSTS_SECONDS=10886400, SECURE_HSTS_PRELOAD=True)
    def test_sts_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD True, the
        middleware adds a "Strict-Transport-Security" header with the "preload"
        directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=10886400; preload",
        )

    @override_settings(
        SECURE_HSTS_SECONDS=10886400,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_sts_subdomains_and_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero, SECURE_HSTS_INCLUDE_SUBDOMAINS and
        SECURE_HSTS_PRELOAD True, the middleware adds a "Strict-Transport-Security"
        header containing both the "includeSubDomains" and "preload" directives
        to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=10886400; includeSubDomains; preload",
        )

    @override_settings(SECURE_HSTS_SECONDS=10886400, SECURE_HSTS_PRELOAD=False)
    def test_sts_no_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD
        False, the middleware adds a "Strict-Transport-Security" header without
        the "preload" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=10886400",
        )

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_on(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "X-Content-Type-Options: nosniff" header to the response.
        """
        self.assertEqual(
            self.process_response().headers["X-Content-Type-Options"],
            "nosniff",
        )

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_already_present(self):
        """
        The middleware will not override an "X-Content-Type-Options" header
        already present in the response.
        """
        response = self.process_response(
            secure=True, headers={"X-Content-Type-Options": "foo"}
        )
        self.assertEqual(response.headers["X-Content-Type-Options"], "foo")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_content_type_off(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "X-Content-Type-Options" header to the response.
        """
        self.assertNotIn("X-Content-Type-Options", self.process_response().headers)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_ssl_redirect_on(self):
        """
        With SECURE_SSL_REDIRECT True, the middleware redirects any non-secure
        requests to the https:// version of the same URL.
        """
        ret = self.process_request("get", "/some/url?query=string")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://testserver/some/url?query=string")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_no_redirect_ssl(self):
        """
        The middleware does not redirect secure requests.
        """
        ret = self.process_request("get", "/some/url", secure=True)
        self.assertIsNone(ret)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=["^insecure/"])
    def test_redirect_exempt(self):
        """
        The middleware does not redirect requests with URL path matching an
        exempt pattern.
        """
        ret = self.process_request("get", "/insecure/page")
        self.assertIsNone(ret)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_SSL_HOST="secure.example.com")
    def test_redirect_ssl_host(self):
        """
        The middleware redirects to SECURE_SSL_HOST if given.
        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://secure.example.com/some/url")

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_ssl_redirect_off(self):
        """
        With SECURE_SSL_REDIRECT False, the middleware does not redirect.
        """
        ret = self.process_request("get", "/some/url")
        self.assertIsNone(ret)

    @override_settings(SECURE_REFERRER_POLICY=None)
    def test_referrer_policy_off(self):
        """
        With SECURE_REFERRER_POLICY set to None, the middleware does not add a
        "Referrer-Policy" header to the response.
        """
        self.assertNotIn("Referrer-Policy", self.process_response().headers)

    def test_referrer_policy_on(self):
        """
        With SECURE_REFERRER_POLICY set to a valid value, the middleware adds a
        "Referrer-Policy" header to the response.
        """
        tests = (
            ("strict-origin", "strict-origin"),
            ("strict-origin,origin", "strict-origin,origin"),
            ("strict-origin, origin", "strict-origin,origin"),
            (["strict-origin", "origin"], "strict-origin,origin"),
            (("strict-origin", "origin"), "strict-origin,origin"),
        )
        for value, expected in tests:
            with (
                self.subTest(value=value),
                override_settings(SECURE_REFERRER_POLICY=value),
            ):
                self.assertEqual(
                    self.process_response().headers["Referrer-Policy"],
                    expected,
                )

    @override_settings(SECURE_REFERRER_POLICY="strict-origin")
    def test_referrer_policy_already_present(self):
        """
        The middleware will not override a "Referrer-Policy" header already
        present in the response.
        """
        response = self.process_response(headers={"Referrer-Policy": "unsafe-url"})
        self.assertEqual(response.headers["Referrer-Policy"], "unsafe-url")

    @override_settings(SECURE_CROSS_ORIGIN_OPENER_POLICY=None)
    def test_coop_off(self):
        """
        With SECURE_CROSS_ORIGIN_OPENER_POLICY set to None, the middleware does
        not add a "Cross-Origin-Opener-Policy" header to the response.
        """
        self.assertNotIn("Cross-Origin-Opener-Policy", self.process_response())

    def test_coop_default(self):
        """SECURE_CROSS_ORIGIN_OPENER_POLICY defaults to same-origin."""
        self.assertEqual(
            self.process_response().headers["Cross-Origin-Opener-Policy"],
            "same-origin",
        )

    def test_coop_on(self):
        """
        With SECURE_CROSS_ORIGIN_OPENER_POLICY set to a valid value, the
        middleware adds a "Cross-Origin_Opener-Policy" header to the response.
        """
        tests = ["same-origin", "same-origin-allow-popups", "unsafe-none"]
        for value in tests:
            with (
                self.subTest(value=value),
                override_settings(
                    SECURE_CROSS_ORIGIN_OPENER_POLICY=value,
                ),
            ):
                self.assertEqual(
                    self.process_response().headers["Cross-Origin-Opener-Policy"],
                    value,
                )

    @override_settings(SECURE_CROSS_ORIGIN_OPENER_POLICY="unsafe-none")
    def test_coop_already_present(self):
        """
        The middleware doesn't override a "Cross-Origin-Opener-Policy" header
        already present in the response.
        """
        response = self.process_response(
            headers={"Cross-Origin-Opener-Policy": "same-origin"}
        )
        self.assertEqual(response.headers["Cross-Origin-Opener-Policy"], "same-origin")

    def test_csp_defaults_off(self):
        response = self.process_response()
        self.assertNotIn(csp.HEADER, response.headers)
        self.assertNotIn(csp.HEADER_REPORT_ONLY, response.headers)

    @override_settings(SECURE_CSP={"DIRECTIVES": {"default-src": [csp.SELF]}})
    def test_csp_basic(self):
        """
        With SECURE_CSP set to a valid value, the middleware adds a
        "Content-Security-Policy" header to the response.
        """
        response = self.process_response()
        self.assertEqual(response.headers[csp.HEADER], "default-src 'self'")
        self.assertNotIn(csp.HEADER_REPORT_ONLY, response.headers)

    @override_settings(
        SECURE_CSP={
            "DIRECTIVES": {"default-src": [csp.SELF, csp.NONCE]},
        }
    )
    def test_csp_basic_with_nonce(self):
        """
        The middleware adds a "Content-Security-Policy" header to the response with a
        nonce if the "default-src" directive includes "csp.NONCE". Since the nonce is
        random and added to the request, we do extra work to get the request object.
        """
        request = self.request.get("/some/url")
        self.middleware().process_request(request)
        self.assertEqual(
            self.process_response(request=request).headers[csp.HEADER],
            f"default-src 'self' 'nonce-{request.csp_nonce}'",
        )

    @override_settings(
        SECURE_CSP_REPORT_ONLY={"DIRECTIVES": {"default-src": [csp.SELF]}}
    )
    def test_csp_report_only_basic(self):
        """
        With SECURE_CSP_REPORT_ONLY set to a valid value, the middleware adds a
        "Content-Security-Policy-Report-Only" header to the response.
        """
        response = self.process_response()
        self.assertEqual(response.headers[csp.HEADER_REPORT_ONLY], "default-src 'self'")
        self.assertNotIn(csp.HEADER, response.headers)

    def test_csp_both(self):
        """
        If both SECURE_CSP and SECURE_CSP_REPORT_ONLY are set, the middleware
        adds both headers to the response.
        """
        with override_settings(
            SECURE_CSP={"DIRECTIVES": {"default-src": [csp.SELF]}},
            SECURE_CSP_REPORT_ONLY={"DIRECTIVES": {"default-src": [csp.SELF]}},
        ):
            response = self.process_response()
            self.assertEqual(response.headers[csp.HEADER], "default-src 'self'")
            self.assertEqual(
                response.headers[csp.HEADER_REPORT_ONLY],
                "default-src 'self'",
            )


class BuildCSPTest(SimpleTestCase):
    def setUp(self):
        from django.middleware.security import build_csp

        self.build_csp = build_csp

    def assertPolicyEqual(self, a, b):
        parts_a = sorted(a.split("; ")) if a is not None else None
        parts_b = sorted(b.split("; ")) if b is not None else None
        self.assertEqual(parts_a, parts_b, f"Policies not equal: {a!r} != {b!r}")

    def test_config_empty(self):
        self.assertPolicyEqual(self.build_csp({}), "")

    def test_config_basic(self):
        policy = {"DIRECTIVES": {"default-src": [csp.SELF]}}
        self.assertPolicyEqual(self.build_csp(policy), "default-src 'self'")

    def test_config_multiple_directives(self):
        policy = {"DIRECTIVES": {"default-src": [csp.SELF], "script-src": [csp.SELF]}}
        self.assertPolicyEqual(
            self.build_csp(policy), "default-src 'self'; script-src 'self'"
        )

    def test_config_value_not_list(self):
        policy = {"DIRECTIVES": {"default-src": csp.SELF}}
        self.assertPolicyEqual(self.build_csp(policy), "default-src 'self'")

    def test_config_value_tuple(self):
        policy = {"DIRECTIVES": {"default-src": (csp.SELF,)}}
        self.assertPolicyEqual(self.build_csp(policy), "default-src 'self'")

    def test_config_value_none(self):
        policy = {"DIRECTIVES": {"default-src": [csp.SELF], "script-src": None}}
        self.assertPolicyEqual(self.build_csp(policy), "default-src 'self'")

    def test_config_value_boolean_true(self):
        policy = {
            "DIRECTIVES": {"default-src": [csp.SELF], "block-all-mixed-content": True}
        }
        self.assertPolicyEqual(
            self.build_csp(policy), "default-src 'self'; block-all-mixed-content"
        )

    def test_config_value_boolean_false(self):
        policy = {
            "DIRECTIVES": {"default-src": [csp.SELF], "block-all-mixed-content": False}
        }
        self.assertPolicyEqual(self.build_csp(policy), "default-src 'self'")

    def test_config_value_multiple_boolean(self):
        policy = {
            "DIRECTIVES": {
                "default-src": [csp.SELF],
                "block-all-mixed-content": True,
                "upgrade-insecure-requests": True,
            }
        }
        self.assertPolicyEqual(
            self.build_csp(policy),
            "default-src 'self'; block-all-mixed-content; upgrade-insecure-requests",
        )

    def test_config_with_nonce_arg(self):
        policy = {"DIRECTIVES": {"default-src": [csp.SELF]}}
        self.assertPolicyEqual(
            self.build_csp(policy, nonce="abc123"), "default-src 'self'"
        )

    def test_config_with_nonce(self):
        policy = {
            "DIRECTIVES": {"default-src": [csp.SELF, csp.NONCE]},
        }
        self.assertPolicyEqual(
            self.build_csp(policy, nonce="abc123"), "default-src 'self' 'nonce-abc123'"
        )

    def test_config_with_multiple_nonces(self):
        policy = {
            "DIRECTIVES": {
                "default-src": [csp.SELF, csp.NONCE],
                "script-src": [csp.SELF, csp.NONCE],
            },
        }
        self.assertPolicyEqual(
            self.build_csp(policy, nonce="abc123"),
            "default-src 'self' 'nonce-abc123'; script-src 'self' 'nonce-abc123'",
        )

    def test_config_with_only_nonce_directive(self):
        policy = {"DIRECTIVES": {"default-src": [csp.NONCE]}}
        self.assertPolicyEqual(
            self.build_csp(policy, nonce="abc123"), "default-src 'nonce-abc123'"
        )

    def test_config_with_empty_directive(self):
        policy = {"DIRECTIVES": {"default-src": []}}
        self.assertPolicyEqual(self.build_csp(policy), "")

    def test_nonce_sentinel(self):
        assert csp.Nonce() == csp.Nonce()
        assert csp.NONCE == csp.Nonce()
        assert repr(csp.Nonce()) == "django.middleware.constants.csp.NONCE"
