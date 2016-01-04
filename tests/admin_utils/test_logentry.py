from __future__ import unicode_literals

from datetime import datetime

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.html import escape

from .models import Article, ArticleProxy, Site


@override_settings(ROOT_URLCONF="admin_utils.urls")
class LogEntryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            password='sha1$995a3$6011485ea3834267d719b4c801409b8b1ddd0158',
            is_superuser=True, username='super',
            first_name='Super', last_name='User', email='super@example.com',
            is_staff=True, is_active=True, date_joined=datetime(2007, 5, 30, 13, 20, 10)
        )
        self.site = Site.objects.create(domain='example.org')
        self.a1 = Article.objects.create(
            site=self.site,
            title="Title",
            created=datetime(2008, 3, 18, 11, 54, 58),
        )
        content_type_pk = ContentType.objects.get_for_model(Article).pk
        LogEntry.objects.log_action(
            self.user.pk, content_type_pk, self.a1.pk, repr(self.a1), CHANGE,
            change_message='Changed something'
        )
        self.client.force_login(self.user)

    def test_logentry_save(self):
        """
        LogEntry.action_time is a timestamp of the date when the entry was
        created. It shouldn't be updated on a subsequent save().
        """
        logentry = LogEntry.objects.get(content_type__model__iexact="article")
        action_time = logentry.action_time
        logentry.save()
        self.assertEqual(logentry.action_time, action_time)

    def test_logentry_get_edited_object(self):
        """
        LogEntry.get_edited_object() returns the edited object of a LogEntry
        object.
        """
        logentry = LogEntry.objects.get(content_type__model__iexact="article")
        edited_obj = logentry.get_edited_object()
        self.assertEqual(logentry.object_id, str(edited_obj.pk))

    def test_logentry_get_admin_url(self):
        """
        LogEntry.get_admin_url returns a URL to edit the entry's object or
        None for non-existent (possibly deleted) models.
        """
        logentry = LogEntry.objects.get(content_type__model__iexact='article')
        expected_url = reverse('admin:admin_utils_article_change', args=(quote(self.a1.pk),))
        self.assertEqual(logentry.get_admin_url(), expected_url)
        self.assertIn('article/%d/change/' % self.a1.pk, logentry.get_admin_url())

        logentry.content_type.model = "non-existent"
        self.assertIsNone(logentry.get_admin_url())

    def test_logentry_unicode(self):
        log_entry = LogEntry()

        log_entry.action_flag = ADDITION
        self.assertTrue(six.text_type(log_entry).startswith('Added '))

        log_entry.action_flag = CHANGE
        self.assertTrue(six.text_type(log_entry).startswith('Changed '))

        log_entry.action_flag = DELETION
        self.assertTrue(six.text_type(log_entry).startswith('Deleted '))

        # Make sure custom action_flags works
        log_entry.action_flag = 4
        self.assertEqual(six.text_type(log_entry), 'LogEntry Object')

    def test_recentactions_without_content_type(self):
        """
        If a LogEntry is missing content_type it will not display it in span
        tag under the hyperlink.
        """
        response = self.client.get(reverse('admin:index'))
        link = reverse('admin:admin_utils_article_change', args=(quote(self.a1.pk),))
        should_contain = """<a href="%s">%s</a>""" % (escape(link), escape(repr(self.a1)))
        self.assertContains(response, should_contain)
        should_contain = "Article"
        self.assertContains(response, should_contain)
        logentry = LogEntry.objects.get(content_type__model__iexact='article')
        # If the log entry doesn't have a content type it should still be
        # possible to view the Recent Actions part (#10275).
        logentry.content_type = None
        logentry.save()

        counted_presence_before = response.content.count(force_bytes(should_contain))
        response = self.client.get(reverse('admin:index'))
        counted_presence_after = response.content.count(force_bytes(should_contain))
        self.assertEqual(counted_presence_before - 1, counted_presence_after)

    def test_proxy_model_content_type_is_used_for_log_entries(self):
        """
        Log entries for proxy models should have the proxy model's contenttype
        (#21084).
        """
        proxy_content_type = ContentType.objects.get_for_model(ArticleProxy, for_concrete_model=False)
        post_data = {
            'site': self.site.pk, 'title': "Foo", 'title2': "Bar",
            'created_0': '2015-12-25', 'created_1': '00:00',
        }
        changelist_url = reverse('admin:admin_utils_articleproxy_changelist')

        # add
        proxy_add_url = reverse('admin:admin_utils_articleproxy_add')
        response = self.client.post(proxy_add_url, post_data)
        self.assertRedirects(response, changelist_url)
        proxy_addition_log = LogEntry.objects.latest('id')
        self.assertEqual(proxy_addition_log.action_flag, ADDITION)
        self.assertEqual(proxy_addition_log.content_type, proxy_content_type)

        # change
        article_id = proxy_addition_log.object_id
        proxy_change_url = reverse('admin:admin_utils_articleproxy_change', args=(article_id,))
        post_data['title'] = 'New'
        response = self.client.post(proxy_change_url, post_data)
        self.assertRedirects(response, changelist_url)
        proxy_change_log = LogEntry.objects.latest('id')
        self.assertEqual(proxy_change_log.action_flag, CHANGE)
        self.assertEqual(proxy_change_log.content_type, proxy_content_type)

        # delete
        proxy_delete_url = reverse('admin:admin_utils_articleproxy_delete', args=(article_id,))
        response = self.client.post(proxy_delete_url, {'post': 'yes'})
        self.assertRedirects(response, changelist_url)
        proxy_delete_log = LogEntry.objects.latest('id')
        self.assertEqual(proxy_delete_log.action_flag, DELETION)
        self.assertEqual(proxy_delete_log.content_type, proxy_content_type)
