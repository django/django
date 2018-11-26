from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import background


class PermissionsRequiredDecoratorTest(TestCase):
    """
    Tests background task processing using asyncio or concurrent.futures.ThreadPoolExecutor
    """
    def setUp(self):
        self.factory = RequestFactory()

    def test_many_permissions_pass(self):

        def a_view(request):
            @background.task
            def task():
                import time

                time.sleep(3)

            task()

            return HttpResponse("OK")

        request = self.factory.get('/long-task')
        resp = a_view(request)

        assert 'OK' in resp.content
        self.assertEqual(resp.status_code, 200)
