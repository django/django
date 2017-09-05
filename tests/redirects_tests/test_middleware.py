from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.contrib.redirects.models import Redirect
from django.http import (
    HttpResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseRedirect,
)
from django.test import (
    RequestFactory, TestCase, modify_settings, override_settings,
)


@modify_settings(ALLOWED_HOSTS={'append': 'test.loc'})
@override_settings(APPEND_SLASH=False)
class RedirectFallbackMiddlewareTests(TestCase):
    def setUp(self):
        self.middleware = RedirectFallbackMiddleware(
            lambda r: HttpResponseNotFound()
        )
        self.rf = RequestFactory()

    def test_blank_redirect(self):
        r = Redirect.objects.create(domain='', old_path='/old', new_path='/new')
        request = self.rf.get(r.old_path)

        response = self.middleware(request)

        self.assertRedirects(response, r.new_path,
                             status_code=301, fetch_redirect_response=False)

    def test_domain_redirect(self):
        r = Redirect.objects.create(domain='test.loc', old_path='/old', new_path='/new')
        request = self.rf.get(r.old_path, HTTP_HOST=r.domain)

        response = self.middleware(request)

        self.assertRedirects(response, r.new_path,
                             status_code=301, fetch_redirect_response=False)

    def test_domain_over_blank(self):
        r_blank = Redirect.objects.create(domain='', old_path='/old', new_path='/blank')
        r_domain = Redirect.objects.create(domain='test.loc', old_path='/old', new_path='/domain')

        request = self.rf.get('/old', HTTP_HOST=r_domain.domain)
        response = self.middleware(request)
        self.assertRedirects(response, r_domain.new_path,
                             status_code=301, fetch_redirect_response=False)

        # domain not found, use blank request
        request = self.rf.get('/old', HTTP_HOST='testserver')
        response = self.middleware(request)
        self.assertRedirects(response, r_blank.new_path,
                             status_code=301, fetch_redirect_response=False)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash(self):
        r = Redirect.objects.create(old_path='/old/', new_path='/new')
        request = self.rf.get('/old')

        response = self.middleware(request)

        self.assertRedirects(response, r.new_path,
                             status_code=301, fetch_redirect_response=False)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash_and_query_string(self):
        r = Redirect.objects.create(old_path='/old/?foo', new_path='/new')
        request = self.rf.get('/old?foo')

        response = self.middleware(request)

        self.assertRedirects(response, r.new_path,
                             status_code=301, fetch_redirect_response=False)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_not_found(self):
        """No redirect found neither with slash nor without it."""
        request = self.rf.get('/test')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 404)

    def test_non_404_response(self):
        """If response is not 404, do not redirect."""
        Redirect.objects.create(old_path='/', new_path='/new')
        middleware = RedirectFallbackMiddleware(
            lambda r: HttpResponse(status=200)
        )
        request = self.rf.get('/')

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_response_gone(self):
        """When the redirect target is '', return a 410"""
        r = Redirect.objects.create(old_path='/old', new_path='')
        request = self.rf.get(r.old_path)

        response = self.middleware(request)

        self.assertEqual(response.status_code, 410)


class OverriddenRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    response_gone_class = HttpResponseForbidden
    response_redirect_class = HttpResponseRedirect


class OverriddenRedirectMiddlewareTests(TestCase):
    def setUp(self):
        self.middleware = OverriddenRedirectFallbackMiddleware(
            lambda r: HttpResponseNotFound()
        )
        self.rf = RequestFactory()

    def test_response_gone_class(self):
        r = Redirect.objects.create(old_path='/old/', new_path='')
        request = self.rf.get(r.old_path)

        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_response_redirect_class(self):
        r = Redirect.objects.create(old_path='/old', new_path='/new')
        request = self.rf.get(r.old_path)

        response = self.middleware(request)

        self.assertEqual(response.status_code, 302)
