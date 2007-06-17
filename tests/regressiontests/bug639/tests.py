"""
Tests for file field behavior, and specifically #639, in which Model.save() gets
called *again* for each FileField. This test will fail if calling an
auto-manipulator's save() method causes Model.save() to be called more than once.
"""

import os
import unittest
from regressiontests.bug639.models import Photo
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

class Bug639Test(unittest.TestCase):
        
    def testBug639(self):
        """
        Simulate a file upload and check how many times Model.save() gets called.
        """
        # Grab an image for testing
        img = open(os.path.join(os.path.dirname(__file__), "test.jpg"), "rb").read()
        
        # Fake a request query dict with the file
        qd = QueryDict("title=Testing&image=", mutable=True)
        qd["image_file"] = {
            "filename" : "test.jpg",
            "content-type" : "image/jpeg",
            "content" : img
        }
        
        manip = Photo.AddManipulator()
        manip.do_html2python(qd)
        p = manip.save(qd)
        
        # Check the savecount stored on the object (see the model)
        self.assertEqual(p._savecount, 1)
        
    def tearDown(self):
        """
        Make sure to delete the "uploaded" file to avoid clogging /tmp.
        """
        p = Photo.objects.get()
        os.unlink(p.get_image_filename())