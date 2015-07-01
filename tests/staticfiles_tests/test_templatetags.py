from __future__ import unicode_literals

from .cases import StaticFilesTestCase


class TestTemplateTag(StaticFilesTestCase):

    def test_template_tag(self):
        self.assertStaticRenders("does/not/exist.png", "/static/does/not/exist.png")
        self.assertStaticRenders("testfile.txt", "/static/testfile.txt")
