import urllib, os

from django.test import TestCase
from django.conf import settings
from django.core.files import temp as tempfile

FILE_SIZE = 2 ** 10
CONTENT = 'a' * FILE_SIZE

class SendFileTests(TestCase):
    def test_sendfile(self):
        tdir = tempfile.gettempdir()
        file1 = tempfile.NamedTemporaryFile(suffix=".pdf", dir=tdir)
        file1.write(CONTENT)
        file1.seek(0)

        response = self.client.get('/sendfile/serve_file/%s/' %
                urllib.quote(file1.name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response[settings.HTTPRESPONSE_SENDFILE_HEADER],
                file1.name)
        self.assertEqual(response['Content-Disposition'],
                'attachment; filename=%s' % os.path.basename(file1.name))
        self.assertEqual(response['Content-Length'], str(FILE_SIZE))
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # *if* the degraded case is to be supported, add this instead:
        self.assertEqual(response.content, CONTENT)
        get_content = lambda: response.content.read()
        #self.assertRaises(TypeError, get_content)

        file1.close()
        # TODO: test middleware bypass etc
