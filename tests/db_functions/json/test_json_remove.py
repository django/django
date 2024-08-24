from django.db import NotSupportedError
from django.db.models import JSONField, Value
from django.db.models.functions.json import JSONRemove
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..models import UserPreferences


@skipUnlessDBFeature("supports_partial_json_update")
class JSONRemoveTests(TestCase):
    def test_remove_single_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "font": "Arial"}
        )
        UserPreferences.objects.update(settings=JSONRemove("settings", "theme"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"font": "Arial"})

    def test_remove_nonexistent_key(self):
        user_preferences = UserPreferences.objects.create(settings={"theme": "dark"})
        UserPreferences.objects.update(settings=JSONRemove("settings", "font"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"theme": "dark"})

    def test_remove_nested_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20, "color": "red"}}
        )
        UserPreferences.objects.update(settings=JSONRemove("settings", "font__color"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"font": {"size": 20}})

    def test_remove_multiple_keys(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        UserPreferences.objects.update(
            settings=JSONRemove("settings", "font__color", "theme")
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"font": {"size": 20}})

    def test_remove_keys_with_recursive_call(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        UserPreferences.objects.update(
            settings=JSONRemove(JSONRemove("settings", "font__color"), "theme")
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"font": {"size": 20}})

    def test_save_on_model_field(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "font": "Arial"}
        )
        user_preferences.settings = JSONRemove("settings", "theme")
        user_preferences.save()

        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(user_preferences.settings, {"font": "Arial"})

    def test_update_or_create_not_created(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"color": "black", "font": "Arial"},
                "notifications": {"email": False, "sms": True},
            }
        )

        updated_user_preferences, created = UserPreferences.objects.update_or_create(
            defaults={"settings": JSONRemove("settings", "theme__color")},
            id=user_preferences.id,
        )
        self.assertIs(created, False)
        # Refresh the object to avoid expression persistence after the update.
        updated_user_preferences.refresh_from_db()
        self.assertEqual(
            updated_user_preferences.settings,
            {
                "theme": {"font": "Arial"},
                "notifications": {"email": False, "sms": True},
            },
        )

    def test_update_or_create_created(self):
        updated_user_preferences, created = UserPreferences.objects.update_or_create(
            defaults={"settings": JSONRemove("settings", "theme")},
            id=9999,
            create_defaults={
                "settings": JSONRemove(
                    Value(
                        {"theme": "dark", "notifications": True},
                        output_field=JSONField(),
                    ),
                    "theme",
                )
            },
        )
        self.assertIs(created, True)
        updated_user_preferences.refresh_from_db()
        self.assertEqual(updated_user_preferences.id, 9999)
        self.assertEqual(
            updated_user_preferences.settings,
            {"notifications": True},
        )


class InvalidJSONRemoveTests(TestCase):
    @skipIfDBFeature("supports_partial_json_update")
    def test_remove_not_supported(self):
        with self.assertRaisesMessage(
            NotSupportedError, "JSONRemove() is not supported on this database backend."
        ):
            UserPreferences.objects.create(settings={"theme": "dark", "font": "Arial"})
            UserPreferences.objects.update(settings=JSONRemove("settings", "theme"))

    def test_remove_missing_path_to_be_removed_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONRemove requires at least one path to remove"
        ):
            UserPreferences.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreferences.objects.update(settings=JSONRemove("settings"))
