"""Regression tests for CookieStorage cache variation (#19649)."""

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.template.response import SimpleTemplateResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path

MARKER = "SYNTHETIC_A_ONLY_MESSAGE_19649"
hits = {}


def seed(request):
    messages.info(request, MARKER)
    response = HttpResponse("seeded")
    response["Cache-Control"] = "no-store"
    return response


def seed_cacheable(request):
    hits["seed_cacheable"] = hits.get("seed_cacheable", 0) + 1
    messages.info(request, MARKER)
    return HttpResponse("seeded")


def show(request):
    hits["show"] = hits.get("show", 0) + 1
    return HttpResponse(
        "|".join(str(message) for message in messages.get_messages(request))
    )


def show_count(request):
    hits["count"] = hits.get("count", 0) + 1
    return HttpResponse(str(len(messages.get_messages(request))))


def read_but_ignore(request):
    hits["ignored"] = hits.get("ignored", 0) + 1
    len(messages.get_messages(request))
    return HttpResponse("constant")


def late_render(request):
    return SimpleTemplateResponse(
        "late.html", {"storage": messages.get_messages(request)}
    )


def preserve_vary(request):
    len(messages.get_messages(request))
    response = HttpResponse("constant")
    response["Vary"] = "Accept-Language"
    return response


def do_not_read(request):
    hits["unread"] = hits.get("unread", 0) + 1
    return HttpResponse("constant")


def use_session(request):
    request.session.get("key")
    return HttpResponse("session")


def use_csrf(request):
    get_token(request)
    return HttpResponse("csrf")


urlpatterns = [
    path("seed/", seed),
    path("seed-cacheable/", seed_cacheable),
    path("show/", show),
    path("count/", show_count),
    path("ignored/", read_but_ignore),
    path("late/", late_render),
    path("preserve-vary/", preserve_vary),
    path("unread/", do_not_read),
    path("session/", use_session),
    path("csrf/", use_csrf),
]


@override_settings(
    ROOT_URLCONF="messages_tests.test_cache_vary",
    ALLOWED_HOSTS=["testserver"],
    MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage",
    MIDDLEWARE=[
        "django.middleware.cache.UpdateCacheMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.cache.FetchFromCacheMiddleware",
    ],
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "messages-cache-vary",
        }
    },
    CACHE_MIDDLEWARE_SECONDS=60,
    CACHE_MIDDLEWARE_KEY_PREFIX="messages-cache-vary",
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "OPTIONS": {
                "loaders": [
                    (
                        "django.template.loaders.locmem.Loader",
                        {"late.html": "{{ storage|length }}"},
                    )
                ]
            },
        }
    ],
)
class CookieCacheVaryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        hits.clear()

    def test_a_message_does_not_reach_b_through_shared_cache(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        self.assertIn("messages", a.cookies)
        self.assertNotIn("messages", b.cookies)

        a_response = a.get("/show/")
        b_response = b.get("/show/")
        self.assertEqual(a_response.content.decode(), MARKER)
        self.assertEqual(b_response.content.decode(), "")
        self.assertEqual(hits["show"], 2)
        self.assertEqual(a_response.get("Vary"), "Cookie")

    def test_cookie_absent_first_does_not_hide_later_message(self):
        a = Client()
        b = Client()
        self.assertEqual(b.get("/show/").content.decode(), "")
        a.get("/seed/")
        self.assertEqual(a.get("/show/").content.decode(), MARKER)
        self.assertEqual(hits["show"], 2)

    def test_len_dependent_response_varies_without_consumption(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        self.assertEqual(a.get("/count/").content.decode(), "1")
        self.assertEqual(b.get("/count/").content.decode(), "0")
        self.assertEqual(hits["count"], 2)

    def test_late_template_render_varies(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        self.assertEqual(a.get("/late/").content.decode(), "1")
        self.assertEqual(b.get("/late/").content.decode(), "0")

    def test_add_only_response_is_not_shared_with_another_client(self):
        a = Client()
        b = Client()
        self.assertEqual(a.get("/seed-cacheable/").get("Vary"), "Cookie")
        self.assertEqual(b.get("/seed-cacheable/").get("Vary"), "Cookie")
        self.assertEqual(hits["seed_cacheable"], 2)

    def test_existing_vary_header_is_preserved(self):
        response = Client().get("/preserve-vary/")
        self.assertEqual(response.get("Vary"), "Accept-Language, Cookie")

    def test_unread_messages_leave_cache_behavior_unchanged(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        a_response = a.get("/unread/")
        b_response = b.get("/unread/")
        self.assertEqual(a_response.content.decode(), "constant")
        self.assertEqual(b_response.content.decode(), "constant")
        self.assertNotIn("Cookie", a_response.get("Vary", ""))
        self.assertEqual(hits["unread"], 1)

    @override_settings(
        MIDDLEWARE=[
            "django.middleware.cache.UpdateCacheMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.cache.FetchFromCacheMiddleware",
        ]
    )
    def test_session_and_csrf_vary_are_preserved(self):
        session_response = Client().get("/session/")
        csrf_response = Client().get("/csrf/")
        self.assertEqual(session_response.get("Vary"), "Cookie")
        self.assertEqual(csrf_response.get("Vary"), "Cookie")

    @override_settings(
        MESSAGE_STORAGE="django.contrib.messages.storage.session.SessionStorage",
        MIDDLEWARE=[
            "django.middleware.cache.UpdateCacheMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.cache.FetchFromCacheMiddleware",
        ],
    )
    def test_session_storage_preserves_cache_isolation(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        self.assertIn("sessionid", a.cookies)
        self.assertNotIn("sessionid", b.cookies)
        a_response = a.get("/show/")
        b_response = b.get("/show/")
        self.assertEqual(a_response.content.decode(), MARKER)
        self.assertEqual(b_response.content.decode(), "")
        self.assertEqual(a_response.get("Vary"), "Cookie")
        self.assertEqual(hits["show"], 2)

    @override_settings(
        MESSAGE_STORAGE="django.contrib.messages.storage.fallback.FallbackStorage",
        MIDDLEWARE=[
            "django.middleware.cache.UpdateCacheMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.cache.FetchFromCacheMiddleware",
        ],
    )
    def test_fallback_with_session_and_csrf_does_not_leak(self):
        a = Client()
        b = Client()
        a.get("/seed/")
        self.assertIn("messages", a.cookies)
        self.assertNotIn("messages", b.cookies)
        a_response = a.get("/show/")
        b_response = b.get("/show/")
        self.assertEqual(a_response.content.decode(), MARKER)
        self.assertEqual(b_response.content.decode(), "")
        self.assertEqual(a_response.get("Vary"), "Cookie")
        self.assertEqual(hits["show"], 2)

    def test_read_without_body_use_still_varies(self):
        """The conservative read rule also affects constant responses."""
        a = Client()
        a.get("/seed/")
        response = a.get("/ignored/")
        self.assertEqual(response.content.decode(), "constant")
        self.assertEqual(response.get("Vary"), "Cookie")

    def test_unrelated_cookie_values_split_constant_response_cache(self):
        """Vary: Cookie keys on the entire Cookie header, not only messages."""
        a = Client()
        b = Client()
        a.cookies["unrelated"] = "a"
        b.cookies["unrelated"] = "b"
        self.assertEqual(a.get("/ignored/").content.decode(), "constant")
        self.assertEqual(b.get("/ignored/").content.decode(), "constant")
        self.assertEqual(a.get("/ignored/").content.decode(), "constant")
        self.assertEqual(b.get("/ignored/").content.decode(), "constant")
        self.assertEqual(hits["ignored"], 2)
