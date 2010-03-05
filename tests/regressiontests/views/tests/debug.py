from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

class DebugViewTests(TestCase):
    def setUp(self):
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = False

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
