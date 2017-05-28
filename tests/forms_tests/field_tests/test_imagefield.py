import os
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ImageField, ValidationError
from django.test import SimpleTestCase

try:
    from PIL import Image
except ImportError:
    Image = None


def get_img_path(path):
    return os.path.join(os.path.abspath(os.path.join(__file__, '..', '..')), 'tests', path)


@unittest.skipUnless(Image, "Pillow is required to test ImageField")
class ImageFieldTest(SimpleTestCase):

    def test_imagefield_annotate_with_image_after_clean(self):
        f = ImageField()

        img_path = get_img_path('filepath_test_files/1x1.png')
        with open(img_path, 'rb') as img_file:
            img_data = img_file.read()

        img_file = SimpleUploadedFile('1x1.png', img_data)
        img_file.content_type = 'text/plain'

        uploaded_file = f.clean(img_file)

        self.assertEqual('PNG', uploaded_file.image.format)
        self.assertEqual('image/png', uploaded_file.content_type)

    def test_imagefield_annotate_with_bitmap_image_after_clean(self):
        """
        This also tests the situation when Pillow doesn't detect the MIME type
        of the image (#24948).
        """
        from PIL.BmpImagePlugin import BmpImageFile
        try:
            Image.register_mime(BmpImageFile.format, None)
            f = ImageField()
            img_path = get_img_path('filepath_test_files/1x1.bmp')
            with open(img_path, 'rb') as img_file:
                img_data = img_file.read()

            img_file = SimpleUploadedFile('1x1.bmp', img_data)
            img_file.content_type = 'text/plain'

            uploaded_file = f.clean(img_file)

            self.assertEqual('BMP', uploaded_file.image.format)
            self.assertIsNone(uploaded_file.content_type)
        finally:
            Image.register_mime(BmpImageFile.format, 'image/bmp')

    def test_file_extension_validation(self):
        f = ImageField()
        img_path = get_img_path('filepath_test_files/1x1.png')
        with open(img_path, 'rb') as img_file:
            img_data = img_file.read()
        img_file = SimpleUploadedFile('1x1.txt', img_data)
        with self.assertRaisesMessage(ValidationError, "File extension 'txt' is not allowed."):
            f.clean(img_file)
