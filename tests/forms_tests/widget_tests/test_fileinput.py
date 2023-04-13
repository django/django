from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import FileInput
from django.utils.datastructures import MultiValueDict

from .base import WidgetTest


class FileInputTest(WidgetTest):
    widget = FileInput()

    def test_render(self):
        """
        FileInput widgets never render the value attribute. The old value
        isn't useful if a form is updated or an error occurred.
        """
        self.check_html(self.widget, 'email', 'test@example.com', html='<input type="file" name="email">')
        self.check_html(self.widget, 'email', '', html='<input type="file" name="email">')
        self.check_html(self.widget, 'email', None, html='<input type="file" name="email">')

    def test_value_omitted_from_data(self):
        self.assertIs(self.widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(self.widget.value_omitted_from_data({}, {'field': 'value'}, 'field'), False)

    def test_use_required_attribute(self):
        # False when initial data exists. The file input is left blank by the
        # user to keep the existing, initial value.
        self.assertIs(self.widget.use_required_attribute(None), True)
        self.assertIs(self.widget.use_required_attribute('resume.txt'), False)

    def test_multiple_error(self):
        msg = "FileInput doesn't support uploading multiple files."
        with self.assertRaisesMessage(ValueError, msg):
            FileInput(attrs={"multiple": True})

    def test_value_from_datadict_multiple(self):
        class MultipleFileInput(FileInput):
            allow_multiple_selected = True

        file_1 = SimpleUploadedFile("something1.txt", b"content 1")
        file_2 = SimpleUploadedFile("something2.txt", b"content 2")
        # Uploading multiple files is allowed.
        widget = MultipleFileInput(attrs={"multiple": True})
        value = widget.value_from_datadict(
            data={"name": "Test name"},
            files=MultiValueDict({"myfile": [file_1, file_2]}),
            name="myfile",
        )
        self.assertEqual(value, [file_1, file_2])
        # Uploading multiple files is not allowed.
        widget = FileInput()
        value = widget.value_from_datadict(
            data={"name": "Test name"},
            files=MultiValueDict({"myfile": [file_1, file_2]}),
            name="myfile",
        )
        self.assertEqual(value, file_2)

    def test_multiple_default(self):
        class MultipleFileInput(FileInput):
            allow_multiple_selected = True

        tests = [
            (None, True),
            ({"class": "myclass"}, True),
            ({"multiple": False}, False),
        ]
        for attrs, expected in tests:
            with self.subTest(attrs=attrs):
                widget = MultipleFileInput(attrs=attrs)
                self.assertIs(widget.attrs["multiple"], expected)
