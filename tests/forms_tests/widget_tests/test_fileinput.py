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
        self.check_html(self.widget, 'email', [], html='<input type="file" name="email" />')

    def test_value_omitted_from_data(self):
        self.assertIs(self.widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(self.widget.value_omitted_from_data({}, {'field': 'value'}, 'field'), False)

    def test_get_context(self):
        context = FileInput(multiple=True).get_context('name', None, {})
        self.assertTrue(context['widget']['multiple'])

        context = FileInput(multiple=False).get_context('name', None, {})
        self.assertFalse(context['widget']['multiple'])

    def test_value_from_datadict(self):
        file_list = [SimpleUploadedFile('file1', b''), SimpleUploadedFile('file2', b'')]
        files = MultiValueDict()
        files.setlist('file', file_list)
        values = FileInput().value_from_datadict(data={}, files=files, name='file')
        self.assertEqual(values.name, 'file2')

        values = FileInput(multiple=True).value_from_datadict(data={}, files=files, name='file')
        self.assertEqual(values, file_list)
