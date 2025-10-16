from django.db import NotSupportedError
from django.db.models import IntegerField, JSONField, Sum, Value
from django.db.models.functions import Cast, JSONRemove
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

    def test_remove_nested_keys_to_be_empty_object(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"color": "red"}, "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONRemove("settings", "font__color"),
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "font": {},
                "notifications": True,
            },
        )

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

    def test_remove_special_chars(self):
        test_keys = [
            "CONTROL",
            "single'",
            "dollar$",
            "dot.dot",
            "with space",
            "back\\slash",
            "question?mark",
            "user@name",
            "emo🤡'ji",
            "com,ma",
            "curly{{{brace}}}s",
            "escape\uffff'seq'\uffffue\uffff'nce",
        ]
        for key in test_keys:
            with self.subTest(key=key):
                user_preferences = UserPreferences.objects.create(
                    settings={key: 20, "notifications": True, "font": {"size": 30}}
                )
                UserPreferences.objects.update(settings=JSONRemove("settings", key))
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {"notifications": True, "font": {"size": 30}},
                )

    def test_remove_special_chars_double_quotes(self):
        test_keys = [
            'double"',
            "m\\i@x. m🤡'a,t{{{ch}}}e?d$\"'es\uffff'ca\uffff'pe",
        ]
        for key in test_keys:
            with self.subTest(key=key):
                user_preferences = UserPreferences.objects.create(
                    settings={key: 20, "notifications": True, "font": {"size": 30}}
                )
                UserPreferences.objects.update(settings=JSONRemove("settings", key))
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {"notifications": True, "font": {"size": 30}},
                )

    def test_remove_with_values(self):
        UserPreferences.objects.create(
            settings={"font": {"name": "Arial", "size": 10}, "notifications": True}
        )
        user_preferences_value = (
            UserPreferences.objects.annotate(
                settings_updated=JSONRemove("settings", "font__size")
            )
            .values("settings_updated", "settings__font__size")
            .first()
        )

        self.assertEqual(
            user_preferences_value,
            {
                "settings_updated": {"font": {"name": "Arial"}, "notifications": True},
                "settings__font__size": 10,
            },
        )

    def test_remove_with_values_list(self):
        UserPreferences.objects.create(
            settings={"font": {"name": "Arial", "size": 10}, "notifications": True}
        )
        UserPreferences.objects.create(
            settings={
                "font": {"name": "Comic Sans", "size": 20},
                "notifications": False,
            }
        )
        user_preferences_values = UserPreferences.objects.annotate(
            settings_updated=JSONRemove("settings", "font__size")
        ).values_list("settings_updated", flat=True)

        self.assertEqual(
            user_preferences_values[0],
            {"font": {"name": "Arial"}, "notifications": True},
        )

        self.assertEqual(
            user_preferences_values[1],
            {"font": {"name": "Comic Sans"}, "notifications": False},
        )

    def test_remove_with_aggregate(self):
        UserPreferences.objects.create(
            settings={"font": {"name": "Arial", "size": 10}, "notifications": True}
        )
        UserPreferences.objects.create(
            settings={"font": {"name": "Comic Sans", "size": 20}, "notifications": True}
        )
        result = UserPreferences.objects.annotate(
            settings_updated=JSONRemove("settings", "font__size")
        ).aggregate(
            total_font_size=Sum(
                Cast(
                    "settings_updated__font__size",
                    IntegerField(),
                )
            )
        )

        self.assertEqual(result["total_font_size"], None)


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
