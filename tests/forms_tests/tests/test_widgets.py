from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.test import override_settings
from django.urls import reverse

from ..models import Article


@override_settings(ROOT_URLCONF="forms_tests.urls")
class LiveWidgetTests(AdminPlaywrightTestCase):
    available_apps = ["forms_tests"] + AdminPlaywrightTestCase.available_apps

    def test_textarea_trailing_newlines(self):
        """
        A roundtrip on a ModelForm doesn't alter the TextField value
        """
        article = Article.objects.create(content="\nTst\n")
        self.page.goto(
            self.live_server_url + reverse("article_form", args=[article.pk])
        )
        self.page.locator("#submit").click()
        self.page.wait_for_load_state("load")
        article = Article.objects.get(pk=article.pk)
        self.assertEqual(article.content, "\r\nTst\r\n")
