from django.test import SimpleTestCase


class HttpResponseTestCase(SimpleTestCase):
    def assertIsClass(self, object, klass):
        self.assertEqual(type(object), klass)
