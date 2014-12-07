from django.test import SimpleTestCase

from ..utils import setup


class SpacelessTagTests(SimpleTestCase):

    @setup({'spaceless01': "{% spaceless %} <b>    <i> text </i>    </b> {% endspaceless %}"})
    def test_spaceless01(self):
        output = self.engine.render_to_string('spaceless01')
        self.assertEqual(output, "<b><i> text </i></b>")

    @setup({'spaceless02': "{% spaceless %} <b> \n <i> text </i> \n </b> {% endspaceless %}"})
    def test_spaceless02(self):
        output = self.engine.render_to_string('spaceless02')
        self.assertEqual(output, "<b><i> text </i></b>")

    @setup({'spaceless03': "{% spaceless %}<b><i>text</i></b>{% endspaceless %}"})
    def test_spaceless03(self):
        output = self.engine.render_to_string('spaceless03')
        self.assertEqual(output, "<b><i>text</i></b>")

    @setup({'spaceless04': "{% spaceless %}<b>   <i>{{ text }}</i>  </b>{% endspaceless %}"})
    def test_spaceless04(self):
        output = self.engine.render_to_string('spaceless04', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This &amp; that</i></b>")

    @setup({'spaceless05': "{% autoescape off %}{% spaceless %}"
                           "<b>   <i>{{ text }}</i>  </b>{% endspaceless %}"
                           "{% endautoescape %}"})
    def test_spaceless05(self):
        output = self.engine.render_to_string('spaceless05', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This & that</i></b>")

    @setup({'spaceless06': "{% spaceless %}<b>   <i>{{ text|safe }}</i>  </b>{% endspaceless %}"})
    def test_spaceless06(self):
        output = self.engine.render_to_string('spaceless06', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This & that</i></b>")
