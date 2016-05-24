from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ClearableFileInput
from django.utils.encoding import python_2_unicode_compatible

from .base import WidgetTest


@python_2_unicode_compatible
class FakeFieldFile(object):
    """
    Quacks like a FieldFile (has a .url and unicode representation), but
    doesn't require us to care about storages etc.
    """
    url = 'something'

    def __str__(self):
        return self.url


class ClearableFileInputTest(WidgetTest):
    widget = ClearableFileInput()

    def test_clear_input_renders(self):
        """
        A ClearableFileInput with is_required False and rendered with an
        initial value that is a file renders a clear checkbox.
        """
        self.check_html(self.widget, 'myfile', FakeFieldFile(), html=(
            """
            Currently: <a href="something">something</a>
            <input type="checkbox" name="myfile-clear" id="myfile-clear_id" />
            <label for="myfile-clear_id">Clear</label><br />
            Change: <input type="file" name="myfile" />
            """
        ))

    def test_html_escaped(self):
        """
        A ClearableFileInput should escape name, filename, and URL
        when rendering HTML (#15182).
        """
        @python_2_unicode_compatible
        class StrangeFieldFile(object):
            url = "something?chapter=1&sect=2&copy=3&lang=en"

            def __str__(self):
                return '''something<div onclick="alert('oops')">.jpg'''

        self.check_html(ClearableFileInput(), 'my<div>file', StrangeFieldFile(), html=(
            """
            Currently: <a href="something?chapter=1&amp;sect=2&amp;copy=3&amp;lang=en">
            something&lt;div onclick=&quot;alert(&#39;oops&#39;)&quot;&gt;.jpg</a>
            <input type="checkbox" name="my&lt;div&gt;file-clear" id="my&lt;div&gt;file-clear_id" />
            <label for="my&lt;div&gt;file-clear_id">Clear</label><br />
            Change: <input type="file" name="my&lt;div&gt;file" />
            """
        ))

    def test_clear_input_renders_only_if_not_required(self):
        """
        A ClearableFileInput with is_required=False does not render a clear
        checkbox.
        """
        widget = ClearableFileInput()
        widget.is_required = True
        self.check_html(widget, 'myfile', FakeFieldFile(), html=(
            """
            Currently: <a href="something">something</a> <br />
            Change: <input type="file" name="myfile" />
            """
        ))

    def test_clear_input_renders_only_if_initial(self):
        """
        A ClearableFileInput instantiated with no initial value does not render
        a clear checkbox.
        """
        self.check_html(self.widget, 'myfile', None, html='<input type="file" name="myfile" />')

    def test_clear_input_checked_returns_false(self):
        """
        ClearableFileInput.value_from_datadict returns False if the clear
        checkbox is checked, if not required.
        """
        value = self.widget.value_from_datadict(
            data={'myfile-clear': True},
            files={},
            name='myfile',
        )
        self.assertEqual(value, False)

    def test_clear_input_checked_returns_false_only_if_not_required(self):
        """
        ClearableFileInput.value_from_datadict never returns False if the field
        is required.
        """
        widget = ClearableFileInput()
        widget.is_required = True
        field = SimpleUploadedFile('something.txt', b'content')

        value = widget.value_from_datadict(
            data={'myfile-clear': True},
            files={'myfile': field},
            name='myfile',
        )
        self.assertEqual(value, field)

    def test_html_does_not_mask_exceptions(self):
        """
        A ClearableFileInput should not mask exceptions produced while
        checking that it has a value.
        """
        @python_2_unicode_compatible
        class FailingURLFieldFile(object):
            @property
            def url(self):
                raise ValueError('Canary')

            def __str__(self):
                return 'value'

        with self.assertRaisesMessage(ValueError, 'Canary'):
            self.widget.render('myfile', FailingURLFieldFile())

    def test_url_as_property(self):
        @python_2_unicode_compatible
        class URLFieldFile(object):
            @property
            def url(self):
                return 'https://www.python.org/'

            def __str__(self):
                return 'value'

        html = self.widget.render('myfile', URLFieldFile())
        self.assertInHTML('<a href="https://www.python.org/">value</a>', html)

    def test_return_false_if_url_does_not_exists(self):
        @python_2_unicode_compatible
        class NoURLFieldFile(object):
            def __str__(self):
                return 'value'

        html = self.widget.render('myfile', NoURLFieldFile())
        self.assertHTMLEqual(html, '<input name="myfile" type="file" />')
