import decimal
import json

from django.db import NotSupportedError, connection
from django.db.models import F, IntegerField, JSONField, Sum, Value
from django.db.models.functions import Cast, JSONObject, JSONSet
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..models import UserPreferences


@skipUnlessDBFeature("supports_partial_json_update")
class JSONSetTests(TestCase):
    def test_set_single_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", theme="light"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"theme": "light", "notifications": True}
        )

    def test_nested_key_using_missing_path(self):
        user_preferences = UserPreferences.objects.create(settings={})
        UserPreferences.objects.update(
            settings=JSONSet("settings", theme__color="light")
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        if connection.features.json_set_creates_missing_parent_path:
            self.assertEqual(
                user_preferences.settings,
                {"theme": {"color": "light"}},
            )
        else:
            self.assertEqual(
                user_preferences.settings,
                {},
            )

    def test_set_multiple_keys(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": "dark",
                "font": "Arial",
                "notifications": True,
                "cookies": False,
            }
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings", theme="light", font="Comic Sans", notifications=False
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": "light",
                "font": "Comic Sans",
                "notifications": False,
                "cookies": False,
            },
        )

    def test_set_single_new_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet("settings", font={"name": "Arial", "size": 20})
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": "dark",
                "notifications": True,
                "font": {"name": "Arial", "size": 20},
            },
        )

    def test_set_single_key_in_nested_json_object(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20, "name": "Arial"}, "theme": "dark"}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", font__size=10))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"font": {"size": 10, "name": "Arial"}, "theme": "dark"},
        )

    def test_set_special_chars(self):
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
                UserPreferences.objects.update(
                    settings=JSONSet("settings", **{key: 10})
                )
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {key: 10, "notifications": True, "font": {"size": 30}},
                )

                # Update the nested key.
                UserPreferences.objects.update(
                    settings=JSONSet("settings", font__size=20)
                )
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {key: 10, "notifications": True, "font": {"size": 20}},
                )

    def test_set_special_chars_double_quotes(self):
        test_keys = [
            'double"',
            "m\\i@x. m🤡'a,t{{{ch}}}e?d$\"'es\uffff'ca\uffff'pe",
        ]
        for key in test_keys:
            with self.subTest(key=key):
                user_preferences = UserPreferences.objects.create(
                    settings={key: 20, "notifications": True, "font": {"size": 30}}
                )
                UserPreferences.objects.update(
                    settings=JSONSet("settings", **{key: 10})
                )
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {key: 10, "notifications": True, "font": {"size": 30}},
                )

                # Update the nested key.
                UserPreferences.objects.update(
                    settings=JSONSet("settings", font__size=20)
                )
                user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
                self.assertEqual(
                    user_preferences.settings,
                    {key: 10, "notifications": True, "font": {"size": 20}},
                )

    def test_set_multiple_keys_in_nested_json_object_with_nested_calls(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "font": {"size": 20, "name": "Arial", "bold": False},
                "notifications": True,
            }
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                JSONSet("settings", font__size=10), font__name="Comic Sans"
            )
        )

        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "font": {"size": 10, "name": "Comic Sans", "bold": False},
                "notifications": True,
            },
        )

    def test_set_single_key_with_json_object(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings", theme={"type": "dark", "background_color": "black"}
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": {"type": "dark", "background_color": "black"},
                "notifications": True,
            },
        )

    def test_with_annotated_expression(self):
        UserPreferences.objects.create(settings={"theme": "dark", "font_size": 20})
        obj = (
            UserPreferences.objects.annotate(
                settings_updated=JSONSet(
                    "settings", theme={"type": "dark", "background_color": "black"}
                )
            )
            .annotate(
                settings_updated_again=JSONSet(
                    "settings_updated",
                    theme={"type": "dark", "background_color": "red"},
                )
            )
            .first()
        )
        self.assertEqual(
            obj.settings_updated,
            {"theme": {"type": "dark", "background_color": "black"}, "font_size": 20},
        )
        self.assertEqual(
            obj.settings_updated_again,
            {"theme": {"type": "dark", "background_color": "red"}, "font_size": 20},
        )

    def test_set_single_key_with_nested_json(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"type": "dark", "background_color": "red"},
                "notifications": False,
            }
        )
        # Updating the theme key with a JSON object will replace the entire object for
        # that key instead of merging them.
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                theme={
                    "type": "dark",
                    "background": {
                        "color": {"gradient-1": "black", "gradient-2": "grey"},
                        "opacity": 0.5,
                    },
                },
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": {
                    "type": "dark",
                    "background": {
                        "color": {"gradient-1": "black", "gradient-2": "grey"},
                        "opacity": 0.5,
                    },
                },
                "notifications": False,
            },
        )

    def test_set_single_key_with_list(self):
        user_preferences = UserPreferences.objects.create(
            settings={"colors": ["black", "blue", "red"], "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet("settings", colors=["yellow", "green"])
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"colors": ["yellow", "green"], "notifications": True},
        )

    def test_set_single_key_with_list_using_index(self):
        user_preferences = UserPreferences.objects.create(
            settings={"colors": ["black", "blue", "red"], "notifications": True}
        )
        # Update using an existing index.
        UserPreferences.objects.update(settings=JSONSet("settings", colors__1="yellow"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"colors": ["black", "yellow", "red"], "notifications": True},
        )

        # Update using an index that is equal to the array length. It should append the
        # value to the array.
        UserPreferences.objects.update(settings=JSONSet("settings", colors__3="green"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"colors": ["black", "yellow", "red", "green"], "notifications": True},
        )

        # Update using a nonexistent index that is greater than the array length.
        UserPreferences.objects.update(settings=JSONSet("settings", colors__10="white"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)

        if not connection.features.json_set_array_append_requires_length_as_index:
            # It should append the value to the array if the database supports it.
            if connection.vendor == "oracle":
                # Oracle adds null values to the array to fill the gap.
                self.assertEqual(
                    user_preferences.settings,
                    {
                        "colors": [
                            "black",
                            "yellow",
                            "red",
                            "green",
                            *(6 * [None]),
                            "white",
                        ],
                        "notifications": True,
                    },
                )
            elif connection.vendor in {"postgresql", "mysql"}:
                # PostgreSQL and MySQL append the single value to the array.
                self.assertEqual(
                    user_preferences.settings,
                    {
                        "colors": ["black", "yellow", "red", "green", "white"],
                        "notifications": True,
                    },
                )

            # In both cases, the value is appended to the array.
            self.assertIn("white", user_preferences.settings["colors"])
        else:
            # Some databases require the index to be equal to the array length
            # to append the value to the array, so the value is not appended.
            self.assertEqual(
                user_preferences.settings,
                {
                    "colors": ["black", "yellow", "red", "green"],
                    "notifications": True,
                },
            )

    def test_set_using_index_on_non_array(self):
        user_preferences = UserPreferences.objects.create(
            settings={"colors": "yellow", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", colors__5="green"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)

        if connection.features.json_set_wraps_non_array_to_array:
            self.assertEqual(
                user_preferences.settings,
                {"colors": ["yellow", "green"], "notifications": True},
            )
        else:
            self.assertEqual(
                user_preferences.settings,
                {"colors": "yellow", "notifications": True},
            )

    def test_set_single_key_with_json_null(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        # Set the value to JSON null.
        UserPreferences.objects.update(settings=JSONSet("settings", theme=None))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": None, "notifications": True},
        )

    def test_save_on_model_field(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20}, "notifications": True}
        )
        # Use JSONSet as an expression directly on the field of the model instance.
        user_preferences.settings = JSONSet("settings", font__size=30)
        user_preferences.save()

        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"font": {"size": 30}, "notifications": True},
        )

    def test_using_custom_encoder_on_model_field(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"type": "dark", "opacity": decimal.Decimal("100.0")},
                "notifications": True,
            }
        )
        # The settings field uses DjangoJSONEncoder and JSONSet should pick it up.
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                theme__opacity=decimal.Decimal("50.0"),
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": {"type": "dark", "opacity": "50.0"}, "notifications": True},
        )

    def test_using_explicit_custom_encoder(self):
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return str(o.quantize(decimal.Decimal("0.01")))
                return super().default(o)

        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"type": "dark", "opacity": decimal.Decimal("100.0")},
                "notifications": True,
            }
        )
        # We pass a JSONField with a custom encoder as the output field of JSONSet.
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                output_field=JSONField(encoder=CustomJSONEncoder),
                theme__opacity=decimal.Decimal("50.0"),
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": {"type": "dark", "opacity": "50.00"}, "notifications": True},
        )

    def test_set_single_key_using_jsonobject(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                theme=JSONObject(opacity=Value(0.75)),
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": {"opacity": 0.75}, "notifications": True},
        )

    def test_set_single_key_using_expressions(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", id=F("id")))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": "dark", "notifications": True, "id": user_preferences.pk},
        )

    def test_update_or_create_not_created(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"color": "black", "font": "Arial"},
                "notifications": {"email": False, "sms": True},
            }
        )

        updated_user_preferences, created = UserPreferences.objects.update_or_create(
            defaults={"settings": JSONSet("settings", theme__color="white")},
            id=user_preferences.id,
            create_defaults={
                "settings": JSONSet(
                    Value({}, output_field=JSONField()),
                    theme="dark",
                )
            },
        )
        self.assertIs(created, False)
        # Refresh the object to avoid expression persistence after the update.
        updated_user_preferences.refresh_from_db()
        self.assertEqual(
            updated_user_preferences.settings,
            {
                "theme": {"color": "white", "font": "Arial"},
                "notifications": {"email": False, "sms": True},
            },
        )

    def test_update_or_create_created(self):
        updated_user_preferences, created = UserPreferences.objects.update_or_create(
            defaults={
                "settings": JSONSet("settings", theme="dark"),
            },
            id=9999,
            create_defaults={
                "settings": JSONSet(
                    Value({}, output_field=JSONField()),
                    theme="dark",
                )
            },
        )
        self.assertIs(created, True)
        updated_user_preferences.refresh_from_db()
        self.assertEqual(updated_user_preferences.id, 9999)
        self.assertEqual(
            updated_user_preferences.settings,
            {"theme": "dark"},
        )

    def test_set_with_values(self):
        UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        user_preferences_value = (
            UserPreferences.objects.annotate(
                settings_updated=JSONSet("settings", theme="light")
            )
            .values("settings_updated", "settings__theme")
            .first()
        )

        self.assertEqual(
            user_preferences_value,
            {
                "settings_updated": {"theme": "light", "notifications": True},
                "settings__theme": "dark",
            },
        )

    def test_set_with_values_list(self):
        UserPreferences.objects.create(
            settings={"font": "Arial", "theme": "dark", "notifications": True}
        )
        UserPreferences.objects.create(
            settings={"font": "Comic Sans", "theme": "default", "notifications": False}
        )
        user_preferences_values = UserPreferences.objects.annotate(
            settings_updated=JSONSet("settings", theme="light")
        ).values_list("settings_updated", flat=True)

        self.assertEqual(
            user_preferences_values[0],
            {"font": "Arial", "theme": "light", "notifications": True},
        )

        self.assertEqual(
            user_preferences_values[1],
            {"font": "Comic Sans", "theme": "light", "notifications": False},
        )

    def test_set_with_aggregate(self):
        UserPreferences.objects.create(
            settings={"font": {"name": "Arial", "size": 10}, "notifications": True}
        )
        UserPreferences.objects.create(
            settings={"font": {"name": "Comic Sans", "size": 20}, "notifications": True}
        )
        result = UserPreferences.objects.annotate(
            settings_updated=JSONSet(
                "settings",
                font__size=Cast(F("settings__font__size"), IntegerField()) + 30,
            )
        ).aggregate(
            total_font_size=Sum(
                Cast(
                    "settings_updated__font__size",
                    IntegerField(),
                )
            )
        )

        self.assertEqual(result["total_font_size"], 90)


class InvalidJSONSetTests(TestCase):
    @skipIfDBFeature("supports_partial_json_update")
    def test_not_supported(self):
        with self.assertRaisesMessage(
            NotSupportedError, "JSONSet() is not supported on this database backend."
        ):
            UserPreferences.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreferences.objects.update(settings=JSONSet("settings", theme="light"))

    def test_missing_key_value_raises_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONSet requires at least one key-value pair to be set."
        ):
            UserPreferences.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreferences.objects.update(settings=JSONSet("settings"))
