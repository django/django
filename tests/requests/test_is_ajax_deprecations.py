from django.http import HttpRequest
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango40Warning


@ignore_warnings(category=RemovedInDjango40Warning)
class TestDeprecatedIsAjax(SimpleTestCase):
    def test_is_ajax(self):
        request = HttpRequest()
        self.assertIs(request.is_ajax(), False)
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        self.assertIs(request.is_ajax(), True)
