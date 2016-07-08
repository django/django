from django.test import SimpleTestCase


class WidgetTest(SimpleTestCase):
    beatles = (('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))

    def check_html(self, widget, name, value, html='', attrs=None, **kwargs):
        output = widget.render(name, value, attrs=attrs, **kwargs)
        self.assertHTMLEqual(output, html)
