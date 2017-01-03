from django.forms.renderers import DjangoTemplates, Jinja2
from django.test import SimpleTestCase

try:
    import jinja2
except ImportError:
    jinja2 = None


class WidgetTest(SimpleTestCase):
    beatles = (('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))

    @classmethod
    def setUpClass(cls):
        cls.django_renderer = DjangoTemplates()
        cls.jinja2_renderer = Jinja2() if jinja2 else None
        cls.renderers = [cls.django_renderer] + ([cls.jinja2_renderer] if cls.jinja2_renderer else [])
        super(WidgetTest, cls).setUpClass()

    def check_html(self, widget, name, value, html='', attrs=None, **kwargs):
        if self.jinja2_renderer:
            output = widget.render(name, value, attrs=attrs, renderer=self.jinja2_renderer, **kwargs)
            # Django escapes quotes with '&quot;' while Jinja2 uses '&#34;'.
            self.assertHTMLEqual(output.replace('&#34;', '&quot;'), html)

        output = widget.render(name, value, attrs=attrs, renderer=self.django_renderer, **kwargs)
        self.assertHTMLEqual(output, html)
