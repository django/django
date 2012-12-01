"""
Tests for file field behavior, and specifically #639, in which Model.save()
gets called *again* for each FileField. This test will fail if calling a
ModelForm's save() method causes Model.save() to be called more than once.
"""

from __future__ import absolute_import

import os
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import unittest
from django.utils._os import upath

from .models import Photo, PhotoForm, temp_storage_dir


class Bug639Test(unittest.TestCase):

    def testBug639(self):
        """
        Simulate a file upload and check how many times Model.save() gets
        called.
        """
        # Grab an image for testing.
        filename = os.path.join(os.path.dirname(upath(__file__)), "test.jpg")
        with open(filename, "rb") as fp:
            img = fp.read()

        # Fake a POST QueryDict and FILES MultiValueDict.
        data = {'title': 'Testing'}
        files = {"image": SimpleUploadedFile('test.jpg', img, 'image/jpeg')}

        form = PhotoForm(data=data, files=files)
        p = form.save()

        # Check the savecount stored on the object (see the model).
        self.assertEqual(p._savecount, 1)

    def tearDown(self):
        """
        Make sure to delete the "uploaded" file to avoid clogging /tmp.
        """
        p = Photo.objects.get()
        p.image.delete(save=False)
        shutil.rmtree(temp_storage_dir)
