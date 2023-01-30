import json
from datetime import datetime

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation
from django.utils.html import escape

from .models import Article, ArticleProxy, Car, Site


@override_settings(ROOT_URLCONF="admin_utils.urls")
class LogEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.site = Site.objects.create(domain="example.org")
        cls.a1 = Article.objects.create(
            site=cls.site,
            title="Title",
            created=datetime(2008, 3, 12, 11, 54),
        )
        content_type_pk = ContentType.objects.get_for_model(Article).pk
        LogEntry.objects.log_action(
            cls.user.pk,
            content_type_pk,
            cls.a1.pk,
            repr(cls.a1),
            CHANGE,
            change_message="Changed something",
        )

    def setUp(self):
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

    def test_logentry_change_message(self):
        """
        LogEntry.change_message is stored as a dumped JSON structure to be able
        to get the message dynamically translated at display time.
        """
        post_data = {
            "site": self.site.pk,
            "title": "Changed",
            "hist": "Some content",
            "created_0": "2008-03-12",
            "created_1": "11:54",
        }
        change_url = reverse(
            "admin:admin_utils_article_change", args=[quote(self.a1.pk)]
        )
        response = self.client.post(change_url, post_data)
        self.assertRedirects(response, reverse("admin:admin_utils_article_changelist"))
        logentry = LogEntry.objects.filter(
            content_type__model__iexact="article"
        ).latest("id")
        self.assertEqual(logentry.get_change_message(), "Changed Title and History.")
        with translation.override("fr"):
            self.assertEqual(
                logentry.get_change_message(), "Modification de Title et Historique."
            )

        add_url = reverse("admin:admin_utils_article_add")
        post_data["title"] = "New"
        response = self.client.post(add_url, post_data)
        self.assertRedirects(response, reverse("admin:admin_utils_article_changelist"))
        logentry = LogEntry.objects.filter(
            content_type__model__iexact="article"
        ).latest("id")
        self.assertEqual(logentry.get_change_message(), "Added.")
        with translation.override("fr"):
            self.assertEqual(logentry.get_change_message(), "Ajout.")

    def test_logentry_change_message_not_json(self):
        """LogEntry.change_message was a string before Django 1.10."""
        logentry = LogEntry(change_message="non-JSON string")
        self.assertEqual(logentry.get_change_message(), logentry.change_message)

    def test_logentry_change_message_localized_datetime_input(self):
        """
        Localized date/time inputs shouldn't affect changed form data detection.
        """
        post_data = {
            "site": self.site.pk,
            "title": "Changed",
            "hist": "Some content",
            "created_0": "12/03/2008",
            "created_1": "11:54",
        }
        with translation.override("fr"):
            change_url = reverse(
                "admin:admin_utils_article_change", args=[quote(self.a1.pk)]
            )
            response = self.client.post(change_url, post_data)
            self.assertRedirects(
                response, reverse("admin:admin_utils_article_changelist")
            )
        logentry = LogEntry.objects.filter(
            content_type__model__iexact="article"
        ).latest("id")
        self.assertEqual(logentry.get_change_message(), "Changed Title and History.")

    def test_logentry_change_message_formsets(self):
        """
        All messages for changed formsets are logged in a change message.
        """
        a2 = Article.objects.create(
            site=self.site,
            title="Title second article",
            created=datetime(2012, 3, 18, 11, 54),
        )
        post_data = {
            "domain": "example.com",  # domain changed
            "admin_articles-TOTAL_FORMS": "5",
            "admin_articles-INITIAL_FORMS": "2",
            "admin_articles-MIN_NUM_FORMS": "0",
            "admin_articles-MAX_NUM_FORMS": "1000",
            # Changed title for 1st article
            "admin_articles-0-id": str(self.a1.pk),
            "admin_articles-0-site": str(self.site.pk),
            "admin_articles-0-title": "Changed Title",
            # Second article is deleted
            "admin_articles-1-id": str(a2.pk),
            "admin_articles-1-site": str(self.site.pk),
            "admin_articles-1-title": "Title second article",
            "admin_articles-1-DELETE": "on",
            # A new article is added
            "admin_articles-2-site": str(self.site.pk),
            "admin_articles-2-title": "Added article",
        }
        change_url = reverse(
            "admin:admin_utils_site_change", args=[quote(self.site.pk)]
        )
        response = self.client.post(change_url, post_data)
        self.assertRedirects(response, reverse("admin:admin_utils_site_changelist"))
        self.assertSequenceEqual(Article.objects.filter(pk=a2.pk), [])
        logentry = LogEntry.objects.filter(content_type__model__iexact="site").latest(
            "action_time"
        )
        self.assertEqual(
            json.loads(logentry.change_message),
            [
                {"changed": {"fields": ["Domain"]}},
                {"added": {"object": "Added article", "name": "article"}},
                {
                    "changed": {
                        "fields": ["Title", "not_a_form_field"],
                        "object": "Changed Title",
                        "name": "article",
                    }
                },
                {"deleted": {"object": "Title second article", "name": "article"}},
            ],
        )
        self.assertEqual(
            logentry.get_change_message(),
            "Changed Domain. Added article “Added article”. "
            "Changed Title and not_a_form_field for article “Changed Title”. "
            "Deleted article “Title second article”.",
        )

        with translation.override("fr"):
            self.assertEqual(
                logentry.get_change_message(),
                "Modification de Domain. Ajout de article « Added article ». "
                "Modification de Title et not_a_form_field pour l'objet "
                "article « Changed Title ». "
                "Suppression de article « Title second article ».",
            )

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
        None for nonexistent (possibly deleted) models.
        """
        logentry = LogEntry.objects.get(content_type__model__iexact="article")
        expected_url = reverse(
            "admin:admin_utils_article_change", args=(quote(self.a1.pk),)
        )
        self.assertEqual(logentry.get_admin_url(), expected_url)
        self.assertIn("article/%d/change/" % self.a1.pk, logentry.get_admin_url())

        logentry.content_type.model = "nonexistent"
        self.assertIsNone(logentry.get_admin_url())

    def test_logentry_unicode(self):
        log_entry = LogEntry()

        log_entry.action_flag = ADDITION
        self.assertTrue(str(log_entry).startswith("Added "))

        log_entry.action_flag = CHANGE
        self.assertTrue(str(log_entry).startswith("Changed "))

        log_entry.action_flag = DELETION
        self.assertTrue(str(log_entry).startswith("Deleted "))

        # Make sure custom action_flags works
        log_entry.action_flag = 4
        self.assertEqual(str(log_entry), "LogEntry Object")

    def test_logentry_repr(self):
        logentry = LogEntry.objects.first()
        self.assertEqual(repr(logentry), str(logentry.action_time))

    def test_log_action(self):
        content_type_pk = ContentType.objects.get_for_model(Article).pk
        log_entry = LogEntry.objects.log_action(
            self.user.pk,
            content_type_pk,
            self.a1.pk,
            repr(self.a1),
            CHANGE,
            change_message="Changed something else",
        )
        self.assertEqual(log_entry, LogEntry.objects.latest("id"))

    def test_recentactions_without_content_type(self):
        """
        If a LogEntry is missing content_type it will not display it in span
        tag under the hyperlink.
        """
        response = self.client.get(reverse("admin:index"))
        link = reverse("admin:admin_utils_article_change", args=(quote(self.a1.pk),))
        should_contain = """<a href="%s">%s</a>""" % (
            escape(link),
            escape(repr(self.a1)),
        )
        self.assertContains(response, should_contain)
        should_contain = "Article"
        self.assertContains(response, should_contain)
        logentry = LogEntry.objects.get(content_type__model__iexact="article")
        # If the log entry doesn't have a content type it should still be
        # possible to view the Recent Actions part (#10275).
        logentry.content_type = None
        logentry.save()

        should_contain = should_contain.encode()
        counted_presence_before = response.content.count(should_contain)
        response = self.client.get(reverse("admin:index"))
        counted_presence_after = response.content.count(should_contain)
        self.assertEqual(counted_presence_before - 1, counted_presence_after)

    def test_proxy_model_content_type_is_used_for_log_entries(self):
        """
        Log entries for proxy models should have the proxy model's contenttype
        (#21084).
        """
        proxy_content_type = ContentType.objects.get_for_model(
            ArticleProxy, for_concrete_model=False
        )
        post_data = {
            "site": self.site.pk,
            "title": "Foo",
            "hist": "Bar",
            "created_0": "2015-12-25",
            "created_1": "00:00",
        }
        changelist_url = reverse("admin:admin_utils_articleproxy_changelist")

        # add
        proxy_add_url = reverse("admin:admin_utils_articleproxy_add")
        response = self.client.post(proxy_add_url, post_data)
        self.assertRedirects(response, changelist_url)
        proxy_addition_log = LogEntry.objects.latest("id")
        self.assertEqual(proxy_addition_log.action_flag, ADDITION)
        self.assertEqual(proxy_addition_log.content_type, proxy_content_type)

        # change
        article_id = proxy_addition_log.object_id
        proxy_change_url = reverse(
            "admin:admin_utils_articleproxy_change", args=(article_id,)
        )
        post_data["title"] = "New"
        response = self.client.post(proxy_change_url, post_data)
        self.assertRedirects(response, changelist_url)
        proxy_change_log = LogEntry.objects.latest("id")
        self.assertEqual(proxy_change_log.action_flag, CHANGE)
        self.assertEqual(proxy_change_log.content_type, proxy_content_type)

        # delete
        proxy_delete_url = reverse(
            "admin:admin_utils_articleproxy_delete", args=(article_id,)
        )
        response = self.client.post(proxy_delete_url, {"post": "yes"})
        self.assertRedirects(response, changelist_url)
        proxy_delete_log = LogEntry.objects.latest("id")
        self.assertEqual(proxy_delete_log.action_flag, DELETION)
        self.assertEqual(proxy_delete_log.content_type, proxy_content_type)

    def test_action_flag_choices(self):
        tests = ((1, "Addition"), (2, "Change"), (3, "Deletion"))
        for action_flag, display_name in tests:
            with self.subTest(action_flag=action_flag):
                log = LogEntry(action_flag=action_flag)
                self.assertEqual(log.get_action_flag_display(), display_name)

    def test_log_registrated_entry(self):
        LogEntry.objects.log_action(
            self.user.pk,
            ContentType.objects.get_for_model(Article).pk,
            self.a1.pk,
            "Article changed",
            CHANGE,
            change_message="Article changed message",
        )
        c1 = Car.objects.create()
        LogEntry.objects.log_action(
            self.user.pk,
            ContentType.objects.get_for_model(Car).pk,
            c1.pk,
            "Car created",
            ADDITION,
            change_message="Car created message",
        )
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "Article changed")
        self.assertContains(response, "Car created")

        # site "custom_admin" only renders log entries of registered models
        response = self.client.get(reverse("custom_admin:index"))
        self.assertContains(response, "Article changed")
        self.assertNotContains(response, "Car created")
