from django.test import SimpleTestCase

from ..utils import render, setup


class SpacelessTagTests(SimpleTestCase):

    @setup({'spaceless01': "{% spaceless %} <b>    <i> text </i>    </b> {% endspaceless %}"})
    def test_spaceless01(self):
        output = render('spaceless01')
        self.assertEqual(output, "<b><i> text </i></b>")

    @setup({'spaceless02': "{% spaceless %} <b> \n <i> text </i> \n </b> {% endspaceless %}"})
    def test_spaceless02(self):
        output = render('spaceless02')
        self.assertEqual(output, "<b><i> text </i></b>")

    @setup({'spaceless03': "{% spaceless %}<b><i>text</i></b>{% endspaceless %}"})
    def test_spaceless03(self):
        output = render('spaceless03')
        self.assertEqual(output, "<b><i>text</i></b>")

    @setup({'spaceless04': "{% spaceless %}<b>   <i>{{ text }}</i>  </b>{% endspaceless %}"})
    def test_spaceless04(self):
        output = render('spaceless04', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This &amp; that</i></b>")

    @setup({'spaceless05': "{% autoescape off %}{% spaceless %}"
                           "<b>   <i>{{ text }}</i>  </b>{% endspaceless %}"
                           "{% endautoescape %}"})
    def test_spaceless05(self):
        output = render('spaceless05', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This & that</i></b>")

    @setup({'spaceless06': "{% spaceless %}<b>   <i>{{ text|safe }}</i>  </b>{% endspaceless %}"})
    def test_spaceless06(self):
        output = render('spaceless06', {'text': 'This & that'})
        self.assertEqual(output, "<b><i>This & that</i></b>")
