from __future__ import unicode_literals

from django.contrib.admin.templatetags.admin_modify import SubmitRowNode
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import reverse
from django.utils.encoding import force_text

from .admin import ArticleAdmin, site
from .models import Article
from .tests import AdminViewBasicTestCase


class AdminTemplateTagsTest(AdminViewBasicTestCase):
    def test_submit_row(self):
        """
        submit_row template tag should pass whole context.
        """
        factory = RequestFactory()
        request = factory.get(reverse('admin:auth_user_change', args=[self.superuser.pk]))
        request.user = self.superuser
        admin = UserAdmin(User, site)
        extra_context = {'extra': True}
        response = admin.change_view(request, str(self.superuser.pk), extra_context=extra_context)
        template_context = SubmitRowNode._get_context(response.context_data)
        self.assertIs(template_context['extra'], True)
        self.assertIs(template_context['show_save'], True)

    def test_can_override_submit_row(self):
        """
        submit_row template can follow the 'standard' search patter admin/app_label/model/submit_line.html
        """
        factory = RequestFactory()
        article = Article.objects.all()[0]
        request = factory.get(reverse('admin:admin_views_article_change', args=[article.pk]))
        request.user = self.superuser
        admin = ArticleAdmin(Article, site)
        extra_context = {'show_publish': True}
        response = admin.change_view(request, str(article.pk), extra_context=extra_context)
        response.render()
        self.assertIs(response.context_data['show_publish'], True)
        self.assertIs('name="_publish"' in force_text(response.content), True)
