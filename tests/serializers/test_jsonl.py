import decimal
import json
import re

from django.core import serializers
from django.core.serializers.base import DeserializationError
from django.db import models
from django.test import TestCase, TransactionTestCase
from django.test.utils import isolate_apps

from .models import Score
from .tests import SerializersTestBase, SerializersTransactionTestBase


class JsonlSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "jsonl"
    pkless_str = [
        '{"pk": null,"model": "serializers.category","fields": {"name": "Reference"}}',
        '{"model": "serializers.category","fields": {"name": "Non-fiction"}}',
    ]
    pkless_str = "\n".join([s.replace("\n", "") for s in pkless_str])

    mapping_ordering_str = (
        '{"model": "serializers.article","pk": %(article_pk)s,'
        '"fields": {'
        '"author": %(author_pk)s,'
        '"headline": "Poker has no place on ESPN",'
        '"pub_date": "2006-06-16T11:00:00",'
        '"categories": [%(first_category_pk)s,%(second_category_pk)s],'
        '"meta_data": [],'
        '"topics": []}}\n'
    )

    @staticmethod
    def _validate_output(serial_str):
        try:
            for line in serial_str.split("\n"):
                if line:
                    json.loads(line)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        serial_list = [json.loads(line) for line in serial_str.split("\n") if line]
        return [obj_dict["pk"] for obj_dict in serial_list]

    @staticmethod
    def _get_field_values(serial_str, field_name):
        serial_list = [json.loads(line) for line in serial_str.split("\n") if line]
        return [
            obj_dict["fields"][field_name]
            for obj_dict in serial_list
            if field_name in obj_dict["fields"]
        ]

    def test_no_indentation(self):
        s = serializers.jsonl.Serializer()
        json_data = s.serialize([Score(score=5.0), Score(score=6.0)], indent=2)
        for line in json_data.splitlines():
            self.assertIsNone(re.search(r".+,\s*$", line))

    @isolate_apps("serializers")
    def test_custom_encoder(self):
        class ScoreDecimal(models.Model):
            score = models.DecimalField()

        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return str(o)
                return super().default(o)

        s = serializers.jsonl.Serializer()
        json_data = s.serialize(
            [ScoreDecimal(score=decimal.Decimal(1.0))],
            cls=CustomJSONEncoder,
        )
        self.assertIn('"fields": {"score": "1"}', json_data)

    def test_json_deserializer_exception(self):
        with self.assertRaises(DeserializationError):
            for obj in serializers.deserialize("jsonl", """[{"pk":1}"""):
                pass

    def test_helpful_error_message_invalid_pk(self):
        """
        If there is an invalid primary key, the error message contains the
        model associated with it.
        """
        test_string = (
            '{"pk": "badpk","model": "serializers.player",'
            '"fields": {"name": "Bob","rank": 1,"team": "Team"}}'
        )
        with self.assertRaisesMessage(
            DeserializationError, "(serializers.player:pk=badpk)"
        ):
            list(serializers.deserialize("jsonl", test_string))

    def test_helpful_error_message_invalid_field(self):
        """
        If there is an invalid field value, the error message contains the
        model associated with it.
        """
        test_string = (
            '{"pk": "1","model": "serializers.player",'
            '"fields": {"name": "Bob","rank": "invalidint","team": "Team"}}'
        )
        expected = "(serializers.player:pk=1) field_value was 'invalidint'"
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("jsonl", test_string))

    def test_helpful_error_message_for_foreign_keys(self):
        """
        Invalid foreign keys with a natural key throws a helpful error message,
        such as what the failing key is.
        """
        test_string = (
            '{"pk": 1, "model": "serializers.category",'
            '"fields": {'
            '"name": "Unknown foreign key",'
            '"meta_data": ["doesnotexist","metadata"]}}'
        )
        key = ["doesnotexist", "metadata"]
        expected = "(serializers.category:pk=1) field_value was '%r'" % key
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("jsonl", test_string))

    def test_helpful_error_message_for_many2many_non_natural(self):
        """
        Invalid many-to-many keys throws a helpful error message.
        """
        test_strings = [
            """{
                "pk": 1,
                "model": "serializers.article",
                "fields": {
                    "author": 1,
                    "headline": "Unknown many to many",
                    "pub_date": "2014-09-15T10:35:00",
                    "categories": [1, "doesnotexist"]
                }
            }""",
            """{
                "pk": 1,
                "model": "serializers.author",
                "fields": {"name": "Agnes"}
            }""",
            """{
                "pk": 1,
                "model": "serializers.category",
                "fields": {"name": "Reference"}
            }""",
        ]
        test_string = "\n".join([s.replace("\n", "") for s in test_strings])
        expected = "(serializers.article:pk=1) field_value was 'doesnotexist'"
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("jsonl", test_string))

    def test_helpful_error_message_for_many2many_natural1(self):
        """
        Invalid many-to-many keys throws a helpful error message where one of a
        list of natural keys is invalid.
        """
        test_strings = [
            """{
                "pk": 1,
                "model": "serializers.categorymetadata",
                "fields": {"kind": "author","name": "meta1","value": "Agnes"}
            }""",
            """{
                "pk": 1,
                "model": "serializers.article",
                "fields": {
                    "author": 1,
                    "headline": "Unknown many to many",
                    "pub_date": "2014-09-15T10:35:00",
                    "meta_data": [
                        ["author", "meta1"],
                        ["doesnotexist", "meta1"],
                        ["author", "meta1"]
                    ]
                }
            }""",
            """{
                "pk": 1,
                "model": "serializers.author",
                "fields": {"name": "Agnes"}
            }""",
        ]
        test_string = "\n".join([s.replace("\n", "") for s in test_strings])
        key = ["doesnotexist", "meta1"]
        expected = "(serializers.article:pk=1) field_value was '%r'" % key
        with self.assertRaisesMessage(DeserializationError, expected):
            for obj in serializers.deserialize("jsonl", test_string):
                obj.save()

    def test_helpful_error_message_for_many2many_natural2(self):
        """
        Invalid many-to-many keys throws a helpful error message where a
        natural many-to-many key has only a single value.
        """
        test_strings = [
            """{
                "pk": 1,
                "model": "serializers.article",
                "fields": {
                    "author": 1,
                    "headline": "Unknown many to many",
                    "pub_date": "2014-09-15T10:35:00",
                    "meta_data": [1, "doesnotexist"]
                }
            }""",
            """{
                "pk": 1,
                "model": "serializers.categorymetadata",
                "fields": {"kind": "author","name": "meta1","value": "Agnes"}
            }""",
            """{
                "pk": 1,
                "model": "serializers.author",
                "fields": {"name": "Agnes"}
            }""",
        ]
        test_string = "\n".join([s.replace("\n", "") for s in test_strings])
        expected = "(serializers.article:pk=1) field_value was 'doesnotexist'"
        with self.assertRaisesMessage(DeserializationError, expected):
            for obj in serializers.deserialize("jsonl", test_string, ignore=False):
                obj.save()

    def test_helpful_error_message_for_many2many_not_iterable(self):
        """
        Not iterable many-to-many field value throws a helpful error message.
        """
        test_string = (
            '{"pk": 1,"model": "serializers.m2mdata","fields": {"data": null}}'
        )
        expected = "(serializers.m2mdata:pk=1) field_value was 'None'"
        with self.assertRaisesMessage(DeserializationError, expected):
            next(serializers.deserialize("jsonl", test_string, ignore=False))


class JsonSerializerTransactionTestCase(
    SerializersTransactionTestBase, TransactionTestCase
):
    serializer_name = "jsonl"
    fwd_ref_str = [
        """{
            "pk": 1,
            "model": "serializers.article",
            "fields": {
                "headline": "Forward references pose no problem",
                "pub_date": "2006-06-16T15:00:00",
                "categories": [1],
                "author": 1
            }
        }""",
        """{
            "pk": 1,
            "model": "serializers.category",
            "fields": {"name": "Reference"}
        }""",
        """{
            "pk": 1,
            "model": "serializers.author",
            "fields": {"name": "Agnes"}
        }""",
    ]
    fwd_ref_str = "\n".join([s.replace("\n", "") for s in fwd_ref_str])
