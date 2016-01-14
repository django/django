from django.forms import FileInput

from .base import WidgetTest


class FileInputTest(WidgetTest):
    widget = FileInput()

    def test_render(self):
        """
        FileInput widgets never render the value attribute. The old value
        isn't useful if a form is updated or an error occurred.
        """
        self.check_html(self.widget, 'email', 'test@example.com', html='<input type="file" name="email" />')
        self.check_html(self.widget, 'email', '', html='<input type="file" name="email" />')
        self.check_html(self.widget, 'email', None, html='<input type="file" name="email" />')
