from django.contrib.admin.tests import AdminSeleniumTestCase
from django.forms import CharField, Form, TextInput
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from ..models import Article


@override_settings(ROOT_URLCONF="forms_tests.urls")
class LiveWidgetTests(AdminSeleniumTestCase):
    available_apps = ["forms_tests"] + AdminSeleniumTestCase.available_apps

    def test_textarea_trailing_newlines(self):
        """
        A roundtrip on a ModelForm doesn't alter the TextField value
        """
        from selenium.webdriver.common.by import By

        article = Article.objects.create(content="\nTst\n")
        self.selenium.get(
            self.live_server_url + reverse("article_form", args=[article.pk])
        )
        self.selenium.find_element(By.ID, "submit").click()
        article = Article.objects.get(pk=article.pk)
        self.assertEqual(article.content, "\r\nTst\r\n")


class WidgetPlaceholderTests(SimpleTestCase):
    def test_placeholder_in_input_widget(self):
        widget = TextInput(attrs={"placeholder": "Enter text"})
        output = widget.render("name", "")
        self.assertIn('placeholder="Enter text"', output)

    def test_placeholder_in_field(self):
        class ExampleForm(Form):
            name = CharField(widget=TextInput(attrs={"placeholder": "Your name"}))

        form = ExampleForm()
        self.assertIn('placeholder="Your name"', str(form["name"]))
