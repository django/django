import json
import warnings

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.db import connection
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.deprecation import RemovedInDjango70Warning

from .admin import SubscriberAdmin
from .forms import MediaActionForm
from .models import (
    Actor,
    Answer,
    Book,
    ExternalSubscriber,
    ModelAction,
    Question,
    Subscriber,
    UnchangeableObject,
)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminActionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = ExternalSubscriber.objects.create(
            name="John Doe", email="john@example.org"
        )
        cls.s2 = Subscriber.objects.create(
            name="Max Mustermann", email="max@example.org"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_model_admin_custom_action(self):
        """A custom action defined in a ModelAdmin method."""
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "mail_admin",
            "index": 0,
        }
        self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), action_data
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a ModelAdmin action")

    def test_model_admin_default_delete_action(self):
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk, self.s2.pk],
            "action": "delete_selected",
            "index": 0,
        }
        delete_confirmation_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk, self.s2.pk],
            "action": "delete_selected",
            "post": "yes",
        }
        confirmation = self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), action_data
        )
        self.assertIsInstance(confirmation, TemplateResponse)
        self.assertContains(
            confirmation, "Are you sure you want to delete the selected subscribers?"
        )
        self.assertContains(confirmation, "<h1>Delete multiple objects</h1>")
        self.assertContains(confirmation, "<h2>Summary</h2>")
        self.assertContains(confirmation, "<li>Subscribers: 2</li>")
        self.assertContains(confirmation, "<li>External subscribers: 1</li>")
        self.assertContains(confirmation, ACTION_CHECKBOX_NAME, count=2)
        with CaptureQueriesContext(connection) as ctx:
            self.client.post(
                reverse("admin:admin_views_subscriber_changelist"),
                delete_confirmation_data,
            )
        # Log entries are inserted in bulk.
        self.assertEqual(
            len(
                [
                    q["sql"]
                    for q in ctx.captured_queries
                    if q["sql"].startswith("INSERT")
                ]
            ),
            1,
        )
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_default_delete_action_nonexistent_pk(self):
        self.assertFalse(Subscriber.objects.filter(id=9998).exists())
        action_data = {
            ACTION_CHECKBOX_NAME: ["9998"],
            "action": "delete_selected",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), action_data
        )
        self.assertContains(
            response, "Are you sure you want to delete the selected subscribers?"
        )
        self.assertContains(response, "<ul></ul>", html=True)

    @override_settings(USE_THOUSAND_SEPARATOR=True, NUMBER_GROUPING=3)
    def test_non_localized_pk(self):
        """
        If USE_THOUSAND_SEPARATOR is set, the ids for the objects selected for
        deletion are rendered without separators.
        """
        s = ExternalSubscriber.objects.create(id=9999)
        action_data = {
            ACTION_CHECKBOX_NAME: [s.pk, self.s2.pk],
            "action": "delete_selected",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), action_data
        )
        self.assertTemplateUsed(response, "admin/delete_selected_confirmation.html")
        self.assertContains(response, 'value="9999"')  # Instead of 9,999
        self.assertContains(response, 'value="%s"' % self.s2.pk)

    def test_model_admin_default_delete_action_protected(self):
        """
        The default delete action where some related objects are protected
        from deletion.
        """
        q1 = Question.objects.create(question="Why?")
        a1 = Answer.objects.create(question=q1, answer="Because.")
        a2 = Answer.objects.create(question=q1, answer="Yes.")
        q2 = Question.objects.create(question="Wherefore?")
        action_data = {
            ACTION_CHECKBOX_NAME: [q1.pk, q2.pk],
            "action": "delete_selected",
            "index": 0,
        }
        delete_confirmation_data = action_data.copy()
        delete_confirmation_data["post"] = "yes"
        response = self.client.post(
            reverse("admin:admin_views_question_changelist"), action_data
        )
        self.assertContains(
            response, "would require deleting the following protected related objects"
        )
        self.assertContains(
            response,
            '<li>Answer: <a href="%s">Because.</a></li>'
            % reverse("admin:admin_views_answer_change", args=(a1.pk,)),
            html=True,
        )
        self.assertContains(
            response,
            '<li>Answer: <a href="%s">Yes.</a></li>'
            % reverse("admin:admin_views_answer_change", args=(a2.pk,)),
            html=True,
        )
        # A POST request to delete protected objects displays the page which
        # says the deletion is prohibited.
        response = self.client.post(
            reverse("admin:admin_views_question_changelist"), delete_confirmation_data
        )
        self.assertContains(
            response, "would require deleting the following protected related objects"
        )
        self.assertEqual(Question.objects.count(), 2)

    def test_model_admin_default_delete_action_no_change_url(self):
        """
        The default delete action doesn't break if a ModelAdmin removes the
        change_view URL (#20640).
        """
        obj = UnchangeableObject.objects.create()
        action_data = {
            ACTION_CHECKBOX_NAME: obj.pk,
            "action": "delete_selected",
            "index": "0",
        }
        response = self.client.post(
            reverse("admin:admin_views_unchangeableobject_changelist"), action_data
        )
        # No 500 caused by NoReverseMatch. The page doesn't display a link to
        # the nonexistent change page.
        self.assertContains(
            response, "<li>Unchangeable object: %s</li>" % obj, 1, html=True
        )

    def test_delete_queryset_hook(self):
        delete_confirmation_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk, self.s2.pk],
            "action": "delete_selected",
            "post": "yes",
            "index": 0,
        }
        SubscriberAdmin.overridden = False
        self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), delete_confirmation_data
        )
        # SubscriberAdmin.delete_queryset() sets overridden to True.
        self.assertIs(SubscriberAdmin.overridden, True)
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_delete_selected_uses_get_deleted_objects(self):
        """The delete_selected action uses ModelAdmin.get_deleted_objects()."""
        book = Book.objects.create(name="Test Book")
        data = {
            ACTION_CHECKBOX_NAME: [book.pk],
            "action": "delete_selected",
            "index": 0,
        }
        response = self.client.post(reverse("admin2:admin_views_book_changelist"), data)
        # BookAdmin.get_deleted_objects() returns custom text.
        self.assertContains(response, "a deletable object")

    def test_delete_selected_uses_delete_confirmation_max_display(self):
        book = Book.objects.create(name="Test Book")
        data = {
            ACTION_CHECKBOX_NAME: [book.pk],
            "action": "delete_selected",
            "index": 0,
        }
        response = self.client.post(reverse("admin2:admin_views_book_changelist"), data)
        self.assertContains(response, "a deletable object")
        self.assertContains(response, "…and 2 more objects.")
        self.assertNotContains(response, "another object")
        self.assertNotContains(response, "last object")

    def test_custom_function_mail_action(self):
        """A custom action may be defined in a function."""
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "external_mail",
            "index": 0,
        }
        self.client.post(
            reverse("admin:admin_views_externalsubscriber_changelist"), action_data
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a function action")

    def test_custom_function_action_with_redirect(self):
        """Another custom action defined in a function."""
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "redirect_to",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_externalsubscriber_changelist"), action_data
        )
        self.assertEqual(response.status_code, 302)

    def test_default_redirect(self):
        """
        Actions which don't return an HttpResponse are redirected to the same
        page, retaining the querystring (which may contain changelist info).
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "external_mail",
            "index": 0,
        }
        url = reverse("admin:admin_views_externalsubscriber_changelist") + "?o=1"
        response = self.client.post(url, action_data)
        self.assertRedirects(response, url)

    def test_custom_function_action_streaming_response(self):
        """A custom action may return a StreamingHttpResponse."""
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "download",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_externalsubscriber_changelist"), action_data
        )
        content = b"".join(list(response))
        self.assertEqual(
            content, b"This is the content of the file written by John Doe"
        )
        self.assertEqual(response.status_code, 200)

    def test_custom_function_action_no_perm_response(self):
        """A custom action may returns an HttpResponse with a 403 code."""
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "no_perm",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_externalsubscriber_changelist"), action_data
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"No permission to perform this action")

    def test_actions_ordering(self):
        """Actions are ordered as expected."""
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_changelist")
        )
        self.assertContains(
            response,
            """<label>Action: <select name="action" required>
<option value="" selected>- Select an option -</option>
<option value="delete_selected">Delete selected external subscribers</option>
<option value="redirect_to">Redirect to (Awesome action)</option>
<option value="external_mail">External mail (Another awesome action)</option>
<option value="download">Download selected subscriptions</option>
<option value="no_perm">No permission to run</option>
<option value="custom_action">Custom action</option>
<option value="no_decorator_action">No decorator action</option>
</select>""",
            html=True,
        )

    def test_model_without_action(self):
        """A ModelAdmin might not have any actions."""
        response = self.client.get(
            reverse("admin:admin_views_oldsubscriber_changelist")
        )
        self.assertIsNone(response.context["action_form"])
        self.assertNotContains(
            response,
            '<input type="checkbox" class="action-select"',
            msg_prefix="Found an unexpected action toggle checkboxbox in response",
        )
        self.assertNotContains(response, '<input type="checkbox" class="action-select"')

    def test_model_without_action_still_has_jquery(self):
        """
        A ModelAdmin without any actions still has jQuery included on the page.
        """
        response = self.client.get(
            reverse("admin:admin_views_oldsubscriber_changelist")
        )
        self.assertIsNone(response.context["action_form"])
        self.assertContains(
            response,
            "jquery.min.js",
            msg_prefix=(
                "jQuery missing from admin pages for model with no admin actions"
            ),
        )

    def test_action_column_class(self):
        """The checkbox column class is present in the response."""
        response = self.client.get(reverse("admin:admin_views_subscriber_changelist"))
        self.assertIsNotNone(response.context["action_form"])
        self.assertContains(response, "action-checkbox-column")

    def test_multiple_actions_form(self):
        """
        Actions come from the form whose submit button was pressed (#10618).
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            # Two different actions selected on the two forms...
            "action": ["external_mail", "delete_selected"],
            # ...but "go" was clicked on the top form.
            "index": 0,
        }
        self.client.post(
            reverse("admin:admin_views_externalsubscriber_changelist"), action_data
        )
        # The action sends mail rather than deletes.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a function action")

    def test_media_from_actions_form(self):
        """
        The action form's media is included in the changelist view's media.
        """
        response = self.client.get(reverse("admin:admin_views_subscriber_changelist"))
        media_path = MediaActionForm.Media.js[0]
        self.assertIsInstance(response.context["action_form"], MediaActionForm)
        self.assertIn("media", response.context)
        self.assertIn(media_path, response.context["media"]._js)
        self.assertContains(response, media_path)

    def test_user_message_on_none_selected(self):
        """
        User sees a warning when 'Go' is pressed and no items are selected.
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [],
            "action": "delete_selected",
            "index": 0,
        }
        url = reverse("admin:admin_views_subscriber_changelist")
        response = self.client.post(url, action_data)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        response = self.client.get(response.url)
        msg = (
            "Items must be selected in order to perform actions on them. No items have "
            "been changed."
        )
        self.assertContains(response, msg)
        self.assertEqual(Subscriber.objects.count(), 2)

    def test_user_message_on_no_action(self):
        """
        User sees a warning when 'Go' is pressed and no action is selected.
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk, self.s2.pk],
            "action": "",
            "index": 0,
        }
        url = reverse("admin:admin_views_subscriber_changelist")
        response = self.client.post(url, action_data)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        response = self.client.get(response.url)
        self.assertContains(response, "No action selected.")
        self.assertEqual(Subscriber.objects.count(), 2)

    def test_selection_counter(self):
        """The selection counter is there."""
        response = self.client.get(reverse("admin:admin_views_subscriber_changelist"))
        self.assertContains(response, "0 of 2 selected")

    def test_popup_actions(self):
        """Actions aren't shown in popups."""
        changelist_url = reverse("admin:admin_views_subscriber_changelist")
        response = self.client.get(changelist_url)
        self.assertIsNotNone(response.context["action_form"])
        response = self.client.get(changelist_url + "?%s" % IS_POPUP_VAR)
        self.assertIsNone(response.context["action_form"])

    def test_popup_template_response_on_add(self):
        """
        Success on popups shall be rendered from template in order to allow
        easy customization.
        """
        response = self.client.post(
            reverse("admin:admin_views_actor_add") + "?%s=1" % IS_POPUP_VAR,
            {"name": "Troy McClure", "age": "55", IS_POPUP_VAR: "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.template_name,
            [
                "admin/admin_views/actor/popup_response.html",
                "admin/admin_views/popup_response.html",
                "admin/popup_response.html",
            ],
        )
        self.assertTemplateUsed(response, "admin/popup_response.html")

    def test_popup_template_response_on_change(self):
        instance = Actor.objects.create(name="David Tennant", age=45)
        response = self.client.post(
            reverse("admin:admin_views_actor_change", args=(instance.pk,))
            + "?%s=1" % IS_POPUP_VAR,
            {"name": "David Tennant", "age": "46", IS_POPUP_VAR: "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.template_name,
            [
                "admin/admin_views/actor/popup_response.html",
                "admin/admin_views/popup_response.html",
                "admin/popup_response.html",
            ],
        )
        self.assertTemplateUsed(response, "admin/popup_response.html")

    def test_popup_template_response_on_delete(self):
        instance = Actor.objects.create(name="David Tennant", age=45)
        response = self.client.post(
            reverse("admin:admin_views_actor_delete", args=(instance.pk,))
            + "?%s=1" % IS_POPUP_VAR,
            {IS_POPUP_VAR: "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.template_name,
            [
                "admin/admin_views/actor/popup_response.html",
                "admin/admin_views/popup_response.html",
                "admin/popup_response.html",
            ],
        )
        self.assertTemplateUsed(response, "admin/popup_response.html")

    def test_popup_template_escaping(self):
        popup_response_data = json.dumps(
            {
                "new_value": "new_value\\",
                "obj": "obj\\",
                "value": "value\\",
            }
        )
        context = {
            "popup_response_data": popup_response_data,
        }
        output = render_to_string("admin/popup_response.html", context)
        self.assertIn(r"&quot;value\\&quot;", output)
        self.assertIn(r"&quot;new_value\\&quot;", output)
        self.assertIn(r"&quot;obj\\&quot;", output)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminActionsPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s1 = ExternalSubscriber.objects.create(
            name="John Doe", email="john@example.org"
        )
        cls.s2 = Subscriber.objects.create(
            name="Max Mustermann", email="max@example.org"
        )
        cls.user = User.objects.create_user(
            username="user",
            password="secret",
            email="user@example.com",
            is_staff=True,
        )
        permission = Permission.objects.get(codename="change_subscriber")
        cls.user.user_permissions.add(permission)

    def setUp(self):
        self.client.force_login(self.user)

    def test_model_admin_no_delete_permission(self):
        """
        Permission is denied if the user doesn't have delete permission for the
        model (Subscriber).
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "delete_selected",
        }
        url = reverse("admin:admin_views_subscriber_changelist")
        response = self.client.post(url, action_data)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        response = self.client.get(response.url)
        self.assertContains(response, "No action selected.")

    def test_model_admin_no_delete_permission_externalsubscriber(self):
        """
        Permission is denied if the user doesn't have delete permission for a
        related model (ExternalSubscriber).
        """
        permission = Permission.objects.get(codename="delete_subscriber")
        self.user.user_permissions.add(permission)
        delete_confirmation_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk, self.s2.pk],
            "action": "delete_selected",
            "post": "yes",
        }
        response = self.client.post(
            reverse("admin:admin_views_subscriber_changelist"), delete_confirmation_data
        )
        self.assertEqual(response.status_code, 403)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminDetailActionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.user = User.objects.create_user(
            username="user",
            password="secret",
            email="user@example.com",
            is_staff=True,
        )
        cls.s1 = ExternalSubscriber.objects.create(
            name="John Doe", email="john@example.org"
        )
        content_type = ContentType.objects.get_for_model(ExternalSubscriber)
        for permission_type in ("view", "add", "change", "delete"):
            permission = Permission.objects.get(
                codename=f"{permission_type}_externalsubscriber",
                content_type=content_type,
            )
            cls.user.user_permissions.add(permission)

    def setUp(self):
        self.client.force_login(self.user)

    def test_delete_action_not_available_by_default(self):
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk])
        )
        self.assertNotContains(response, '<option value="delete_selected">', html=True)

    def test_singular_description_used_for_action_on_changeform(self):
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk])
        )
        self.assertContains(
            response,
            '<option value="download">Download subscription</option>',
            html=True,
        )
        self.assertNotContains(response, "Download selected subscriptions")
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_changelist")
        )
        self.assertNotContains(response, "Download subscription")
        self.assertContains(
            response,
            '<option value="download">Download selected subscriptions</option>',
            html=True,
        )

    def test_actions_filtered_by_permissions(self):
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk])
        )
        self.assertNotContains(
            response, '<option value="custom_action">Custom action</option>', html=True
        )
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk])
        )
        self.assertContains(
            response, '<option value="custom_action">Custom action</option>', html=True
        )

    def test_run_action_permissions(self):
        change_url = reverse(
            "admin:admin_views_externalsubscriber_change", args=[self.s1.pk]
        )
        # User doesn't have the permission to run the custom action.
        response = self.client.get(change_url)
        self.assertNotContains(
            response, '<option value="custom_action">Custom action</option>', html=True
        )
        post_data = {
            "CHANGE_FORM-action": "custom_action",
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "index": 0,
        }
        response = self.client.post(change_url, post_data)
        self.assertNotEqual(response.content, b"OK")

        # Add permission for user to run the custom action.
        content_type = ContentType.objects.get_for_model(ExternalSubscriber)
        permission = Permission.objects.create(
            name="custom",
            codename="custom_externalsubscriber",
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)
        response = self.client.get(change_url)
        self.assertContains(
            response, '<option value="custom_action">Custom action</option>', html=True
        )
        response = self.client.post(change_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_select_across_ignored(self):
        ExternalSubscriber.objects.create(name="Bob Bobson", email="bob@example.org")
        change_url = reverse(
            "admin:admin_views_externalsubscriber_change", args=[self.s1.pk]
        )
        post_data = {
            "CHANGE_FORM-action": "download",
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "index": 0,
            "CHANGE_FORM-select-across": True,
        }
        response = self.client.post(change_url, post_data)
        content = b"".join(list(response))
        self.assertEqual(
            content, b"This is the content of the file written by John Doe"
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_action_ordering_and_template(self):
        response = self.client.get(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk])
        )
        self.assertContains(
            response,
            """<label>Action: <select name="CHANGE_FORM-action" required>
            <option value="" selected>- Select an option -</option>
            <option value="external_mail">External mail (Another awesome action)
            </option>
            <option value="download">Download subscription</option>
            <option value="change_view_only_action">Change view</option>
            </select>""",
            html=True,
        )
        self.assertTemplateUsed(response, "admin/change_form_actions.html")

    def test_detail_actions_are_not_present_in_add_view(self):
        response = self.client.get(reverse("admin:admin_views_externalsubscriber_add"))
        self.assertNotContains(
            response,
            "<div class='actions'>",
            html=True,
        )

    def test_dropdown_not_displayed_when_change_form_actions(self):
        self.client.force_login(self.superuser)
        instance = Actor.objects.create(name="David Tennant", age=45)
        response = self.client.get(
            reverse("admin:admin_views_actor_change", args=(instance.pk,))
        )
        self.assertNotContains(
            response,
            "<div class='actions'>",
            html=True,
        )

    def test_update_object_without_action_selected(self):
        buttons = ["_save", "_continue", "_addanother"]
        for button in buttons:
            with self.subTest(button=button):
                self.client.post(
                    reverse(
                        "admin:admin_views_externalsubscriber_change", args=[self.s1.pk]
                    ),
                    {
                        "name": button,
                        "email": "foo@bar.com",
                        "action": "test",
                        button: "Save",
                        "CHANGE_FORM-action": "",
                        ACTION_CHECKBOX_NAME: [self.s1.pk],
                    },
                )
                external_subscriber = ExternalSubscriber.objects.get()
                self.assertEqual(external_subscriber.name, button)
                self.assertEqual(external_subscriber.email, "foo@bar.com")
                self.assertEqual(external_subscriber.action, "test")

    def test_object_is_not_updated_when_action_selected(self):
        self.client.post(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk]),
            {
                "name": "Foo Bar",
                "email": "foo@bar.com",
                "action": "test",
                "CHANGE_FORM-action": "external_mail",
                ACTION_CHECKBOX_NAME: [self.s1.pk],
                "index": 0,
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a function action")
        external_subscriber = ExternalSubscriber.objects.get()
        self.assertEqual(external_subscriber.name, "John Doe")
        self.assertEqual(external_subscriber.email, "john@example.org")
        self.assertEqual(external_subscriber.action, "subscribe")

    def test_redirect_after_an_action(self):
        response = self.client.post(
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk]),
            {
                "CHANGE_FORM-action": "external_mail",
                ACTION_CHECKBOX_NAME: [self.s1.pk],
                "index": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("admin:admin_views_externalsubscriber_change", args=[self.s1.pk]),
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_popup_change_form_has_no_actions(self):
        change_url = reverse(
            "admin:admin_views_externalsubscriber_change", args=[self.s1.pk]
        )
        response = self.client.get(change_url)
        self.assertIsNotNone(response.context["action_form"])
        checkbox = f'<input type="hidden" name="_selected_action" value="{self.s1.pk}">'
        self.assertContains(response, checkbox, html=True)
        response = self.client.get(change_url + "?%s" % IS_POPUP_VAR)
        self.assertIsNone(response.context["action_form"])
        self.assertNotContains(response, checkbox, html=True)

    def test_user_message_on_no_action(self):
        change_url = reverse(
            "admin:admin_views_externalsubscriber_change", args=[self.s1.pk]
        )
        response = self.client.post(
            change_url,
            {
                "CHANGE_FORM-action": "",
                ACTION_CHECKBOX_NAME: [self.s1.pk],
                "index": 0,
            },
        )
        self.assertRedirects(response, change_url, fetch_redirect_response=False)
        response = self.client.get(response.url)
        self.assertContains(response, "No action selected.")

    # RemovedInDjango70Warning.
    def test_overridden_admin_action_methods(self):
        self.client.force_login(self.superuser)
        obj = ModelAction.objects.create()
        change_url = reverse("admin:admin_views_modelaction_change", args=[obj.pk])
        get_actions_overridden_msg = (
            "Overriding get_actions() without the 'action_location' parameter is "
            "deprecated. Update the signature to get_actions(self, request, "
            "action_location=ActionLocation.CHANGE_LIST)."
        )
        with self.assertWarnsMessage(
            RemovedInDjango70Warning, get_actions_overridden_msg
        ):
            response = self.client.get(change_url)
        self.assertNotContains(response, "<div class='actions'>", html=True)

        changelist_url = reverse("admin:admin_views_modelaction_changelist")
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", RemovedInDjango70Warning)
            warnings.filterwarnings("always", category=RemovedInDjango70Warning)
            response = self.client.get(changelist_url)

            message_warnings = [str(warning.message) for warning in warning_list]
            expected_warnings = {
                get_actions_overridden_msg,
                "Overriding get_action_choices() without the 'action_location' "
                "parameter is deprecated. Update the signature to "
                "get_action_choices(self, request, default_choices=None, "
                "action_location=ActionLocation.CHANGE_LIST).",
                "Unpacking an action tuple is deprecated. "
                "Use Action attributes instead.",
                "Using indexes on an action tuple is deprecated. "
                "Use Action attributes instead.",
            }
            self.assertEqual(set(message_warnings), expected_warnings)
        self.assertContains(response, "Delete selected model actions (extra)")

        action_data = {
            ACTION_CHECKBOX_NAME: [obj.pk],
            "action": "delete_selected",
            "index": 0,
        }
        get_actions_overridden_msg = (
            "Overriding get_actions() without the 'action_location' parameter is "
            "deprecated. Update the signature to get_actions(self, request, "
            "action_location=ActionLocation.CHANGE_LIST)."
        )
        with self.assertWarnsMessage(
            RemovedInDjango70Warning, get_actions_overridden_msg
        ):
            response = self.client.post(
                reverse("admin:admin_views_modelaction_changelist"), action_data
            )
        self.assertContains(
            response, "Are you sure you want to delete the selected model action?"
        )
