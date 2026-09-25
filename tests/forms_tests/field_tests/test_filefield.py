import pickle
import unittest

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import validate_image_file_extension
from django.forms import FileField, Form, MultipleFileField, MultipleFileInput
from django.test import SimpleTestCase
from django.utils.datastructures import MultiValueDict

try:
    from PIL import Image  # NOQA
except ImportError:
    HAS_PILLOW = False
else:
    HAS_PILLOW = True


class FileFieldTest(SimpleTestCase):
    def test_filefield_1(self):
        f = FileField()
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("", "")
        self.assertEqual("files/test1.pdf", f.clean("", "files/test1.pdf"))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None, "")
        self.assertEqual("files/test2.pdf", f.clean(None, "files/test2.pdf"))
        no_file_msg = "'No file was submitted. Check the encoding type on the form.'"
        file = SimpleUploadedFile(None, b"")
        file._name = ""
        with self.assertRaisesMessage(ValidationError, no_file_msg):
            f.clean(file)
        with self.assertRaisesMessage(ValidationError, no_file_msg):
            f.clean(file, "")
        self.assertEqual("files/test3.pdf", f.clean(None, "files/test3.pdf"))
        with self.assertRaisesMessage(ValidationError, no_file_msg):
            f.clean("some content that is not a file")
        with self.assertRaisesMessage(
            ValidationError, "'The submitted file is empty.'"
        ):
            f.clean(SimpleUploadedFile("name", None))
        with self.assertRaisesMessage(
            ValidationError, "'The submitted file is empty.'"
        ):
            f.clean(SimpleUploadedFile("name", b""))
        self.assertEqual(
            SimpleUploadedFile,
            type(f.clean(SimpleUploadedFile("name", b"Some File Content"))),
        )
        self.assertIsInstance(
            f.clean(
                SimpleUploadedFile(
                    "我隻氣墊船裝滿晒鱔.txt",
                    "मेरी मँडराने वाली नाव सर्पमीनों से भरी ह".encode(),
                )
            ),
            SimpleUploadedFile,
        )
        self.assertIsInstance(
            f.clean(
                SimpleUploadedFile("name", b"Some File Content"), "files/test4.pdf"
            ),
            SimpleUploadedFile,
        )

    def test_filefield_2(self):
        f = FileField(max_length=5)
        with self.assertRaisesMessage(
            ValidationError,
            "'Ensure this filename has at most 5 characters (it has 18).'",
        ):
            f.clean(SimpleUploadedFile("test_maxlength.txt", b"hello world"))
        self.assertEqual("files/test1.pdf", f.clean("", "files/test1.pdf"))
        self.assertEqual("files/test2.pdf", f.clean(None, "files/test2.pdf"))
        self.assertIsInstance(
            f.clean(SimpleUploadedFile("name", b"Some File Content")),
            SimpleUploadedFile,
        )

    def test_filefield_3(self):
        f = FileField(allow_empty_file=True)
        self.assertIsInstance(
            f.clean(SimpleUploadedFile("name", b"")), SimpleUploadedFile
        )

    def test_filefield_changed(self):
        """
        The value of data will more than likely come from request.FILES. The
        value of initial data will likely be a filename stored in the database.
        Since its value is of no use to a FileField it is ignored.
        """
        f = FileField()

        # No file was uploaded and no initial data.
        self.assertFalse(f.has_changed("", None))

        # A file was uploaded and no initial data.
        self.assertTrue(
            f.has_changed("", {"filename": "resume.txt", "content": "My resume"})
        )

        # A file was not uploaded, but there is initial data
        self.assertFalse(f.has_changed("resume.txt", None))

        # A file was uploaded and there is initial data (file identity is not
        # dealt with here)
        self.assertTrue(
            f.has_changed(
                "resume.txt", {"filename": "resume.txt", "content": "My resume"}
            )
        )

    def test_disabled_has_changed(self):
        f = FileField(disabled=True)
        self.assertIs(f.has_changed("x", "y"), False)

    def test_file_picklable(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(FileField())), FileField)

    def test_file_name_error_param(self):
        tests = [
            (
                FileField(),
                SimpleUploadedFile("empty.txt", b""),
                "empty",
            ),
            (
                FileField(max_length=5),
                SimpleUploadedFile("too-long.txt", b"content"),
                "max_length",
            ),
        ]
        for field, file, code in tests:
            with self.subTest(code=code):
                with self.assertRaises(ValidationError) as cm:
                    field.clean(file)
                self.assertEqual(cm.exception.code, code)
                self.assertEqual(cm.exception.params["file_name"], file.name)


class MultipleFileFieldTest(SimpleTestCase):
    def test_file_multiple(self):
        f = MultipleFileField()
        files = [
            SimpleUploadedFile("name1", b"Content 1"),
            SimpleUploadedFile("name2", b"Content 2"),
        ]
        self.assertEqual(f.clean(files), files)

    def test_file_single(self):
        f = MultipleFileField()
        file = SimpleUploadedFile("name", b"Content")
        self.assertEqual(f.clean(file), [file])

    def test_file_empty(self):
        required = MultipleFileField()
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            required.clean([])
        optional = MultipleFileField(required=False)
        self.assertEqual(optional.clean([]), [])
        self.assertEqual(optional.clean(None), [])

    def test_file_initial(self):
        f = MultipleFileField()
        initial = [
            SimpleUploadedFile("name1", b"Content 1"),
            SimpleUploadedFile("name2", b"Content 2"),
        ]
        self.assertEqual(f.clean([], initial), initial)

    def test_file_multiple_empty(self):
        f = MultipleFileField()
        files = [
            SimpleUploadedFile("empty.txt", b""),
            SimpleUploadedFile("nonempty.txt", b"Some Content"),
        ]
        msg = "'The submitted file empty.txt is empty.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(files)
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(files[::-1])

    def test_file_multiple_max_length(self):
        f = MultipleFileField(max_length=8)
        files = [
            SimpleUploadedFile("too_long.txt", b"Some Content"),
            SimpleUploadedFile("short", b"Some Content"),
        ]
        msg = (
            "'Ensure the filename too_long.txt has at most 8 characters "
            "(it has 12).'"
        )
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(files)
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(files[::-1])

    @unittest.skipUnless(HAS_PILLOW, "Pillow not installed")
    def test_file_multiple_validation(self):
        f = MultipleFileField(validators=[validate_image_file_extension])

        good_files = [
            SimpleUploadedFile("image1.jpg", b"fake JPEG"),
            SimpleUploadedFile("image2.png", b"faux image"),
            SimpleUploadedFile("image3.bmp", b"fraudulent bitmap"),
        ]
        self.assertEqual(f.clean(good_files), good_files)

        evil_files = [
            SimpleUploadedFile("image1.sh", b"#!/bin/bash -c 'echo pwned!'\n"),
            SimpleUploadedFile("image2.png", b"faux image"),
            SimpleUploadedFile("image3.jpg", b"fake JPEG"),
        ]

        evil_rotations = (
            evil_files[i:] + evil_files[:i]  # Rotate by i.
            for i in range(len(evil_files))
        )
        msg = "File extension “sh” is not allowed. Allowed extensions are: "
        for rotated_evil_files in evil_rotations:
            with self.assertRaisesMessage(ValidationError, msg):
                f.clean(rotated_evil_files)

    def test_has_changed(self):
        f = MultipleFileField()
        self.assertIs(f.has_changed(None, None), False)
        self.assertIs(f.has_changed(None, []), False)
        self.assertIs(
            f.has_changed(None, [SimpleUploadedFile("name", b"Content")]), True
        )

    def test_disabled_has_changed(self):
        f = MultipleFileField(disabled=True)
        self.assertIs(
            f.has_changed(None, [SimpleUploadedFile("name", b"Content")]), False
        )

    def test_widget(self):
        f = MultipleFileField()
        self.assertIsInstance(f.widget, MultipleFileInput)
        self.assertIs(f.widget.allow_multiple_selected, True)

    def test_form(self):
        class MultipleFileForm(Form):
            files = MultipleFileField()

        files = [
            SimpleUploadedFile("name1", b"Content 1"),
            SimpleUploadedFile("name2", b"Content 2"),
        ]
        form = MultipleFileForm({}, MultiValueDict({"files": files}))
        self.assertIs(form.is_valid(), True)
        self.assertEqual(form.cleaned_data["files"], files)
        self.assertHTMLEqual(
            str(MultipleFileForm()),
            '<div><label for="id_files">Files:</label>'
            '<input type="file" name="files" multiple required id="id_files"></div>',
        )

    def test_form_required(self):
        class MultipleFileForm(Form):
            files = MultipleFileField()

        form = MultipleFileForm({}, MultiValueDict())
        self.assertIs(form.is_valid(), False)
        self.assertEqual(form.errors["files"], ["This field is required."])

    def test_form_optional(self):
        class MultipleFileForm(Form):
            files = MultipleFileField(required=False)

        form = MultipleFileForm({}, MultiValueDict())
        self.assertIs(form.is_valid(), True)
        self.assertEqual(form.cleaned_data["files"], [])
        self.assertEqual(form.changed_data, [])

    def test_form_initial(self):
        class MultipleFileForm(Form):
            files = MultipleFileField()

        initial = [
            SimpleUploadedFile("name1", b"Content 1"),
            SimpleUploadedFile("name2", b"Content 2"),
        ]
        form = MultipleFileForm({}, MultiValueDict(), initial={"files": initial})
        self.assertIs(form.is_valid(), True)
        self.assertEqual(form.cleaned_data["files"], initial)
        self.assertEqual(form.changed_data, [])
