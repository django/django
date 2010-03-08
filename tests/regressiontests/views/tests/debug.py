from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.core.urlresolvers import reverse

from regressiontests.views import BrokenException, except_args

class DebugViewTests(TestCase):
    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug

    def test_files(self):
        response = self.client.get('/views/raises/')
        self.assertEquals(response.status_code, 500)

        data = {
            'file_data.txt': SimpleUploadedFile('file_data.txt', 'haha'),
        }
        response = self.client.post('/views/raises/', data)
        self.failUnless('file_data.txt' in response.content)
        self.failIf('haha' in response.content)

    def test_404(self):
        response = self.client.get('/views/raises404/')
        self.assertEquals(response.status_code, 404)

    def test_view_exceptions(self):
        for n in range(len(except_args)):
            self.assertRaises(BrokenException, self.client.get,
                reverse('view_exception', args=(n,)))

