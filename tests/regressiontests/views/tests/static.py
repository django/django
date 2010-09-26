import mimetypes
from os import path

from django.test import TestCase
from regressiontests.views.urls import media_dir

class StaticTests(TestCase):
    """Tests django views in django/views/static.py"""

    def test_serve(self):
        "The static view can serve static media"
        media_files = ['file.txt', 'file.txt.gz']
        for filename in media_files:
            response = self.client.get('/views/site_media/%s' % filename)
            file_path = path.join(media_dir, filename)
            self.assertEquals(open(file_path).read(), response.content)
            self.assertEquals(len(response.content), int(response['Content-Length']))
            self.assertEquals(mimetypes.guess_type(file_path)[1], response.get('Content-Encoding', None))

    def test_unknown_mime_type(self):
        response = self.client.get('/views/site_media/file.unknown')
        self.assertEquals('application/octet-stream', response['Content-Type'])

    def test_copes_with_empty_path_component(self):
        file_name = 'file.txt'
        response = self.client.get('/views/site_media//%s' % file_name)
        file = open(path.join(media_dir, file_name))
        self.assertEquals(file.read(), response.content)

