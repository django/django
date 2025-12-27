import datetime
import decimal
import json
import re
from unittest import mock

from django.core import serializers
from django.core.serializers.base import DeserializationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.utils import isolate_apps
from django.utils.translation import gettext_lazy, override

from .models import Article, Author, Category, Score
from .tests import SerializersTestBase, SerializersTransactionTestBase


class JsonSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "json"
    pkless_str = """[
    {
        "pk": null,
        "model": "serializers.category",
        "fields": {"name": "Reference"}
    }, {
        "model": "serializers.category",
        "fields": {"name": "Non-fiction"}
    }]"""
    mapping_ordering_str = """[
{
  "model": "serializers.article",
  "pk": %(article_pk)s,
  "fields": {
    "author": %(author_pk)s,
    "headline": "Poker has no place on ESPN",
    "pub_date": "2006-06-16T11:00:00",
    "categories": [
      %(first_category_pk)s,
      %(second_category_pk)s
    ],
    "meta_data": [],
    "topics": []
  }
}
]
"""

    @staticmethod
    def _validate_output(serial_str):
        try:
            json.loads(serial_str)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        serial_list = json.loads(serial_str)
        return [obj_dict["pk"] for obj_dict in serial_list]

    @staticmethod
    def _get_field_values(serial_str, field_name):
        serial_list = json.loads(serial_str)
        return [
            obj_dict["fields"][field_name]
            for obj_dict in serial_list
            if field_name in obj_dict["fields"]
        ]

    def test_indentation_whitespace(self):
        s = serializers.json.Serializer()
        json_data = s.serialize([Score(score=5.0), Score(score=6.0)], indent=2)
        for line in json_data.splitlines():
            if re.search(r".+,\s*$", line):
                self.assertEqual(line, line.rstrip())

    @isolate_apps("serializers")
    def test_custom_encoder(self):
        class ScoreDecimal(models.Model):
            score = models.DecimalField()

        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return str(o)
                return super().default(o)

        s = serializers.json.Serializer()
        json_data = s.serialize(
            [ScoreDecimal(score=decimal.Decimal(1.0))], cls=CustomJSONEncoder
        )
        self.assertIn('"fields": {"score": "1"}', json_data)

    def test_json_deserializer_exception(self):
        with self.assertRaises(DeserializationError):
            for obj in serializers.deserialize("json", """[{"pk":1}"""):
                pass

    def test_helpful_error_message_invalid_pk(self):
        """
        If there is an invalid primary key, the error message should contain
        the model associated with it.
        """
        test_string = """[{
            "pk": "badpk",
            "model": "serializers.player",
            "fields": {
                "name": "Bob",
                "rank": 1,
                "team": "Team"
            }
        }]"""
        with self.assertRaisesMessage(
            DeserializationError, "(serializers.player:pk=badpk)"
        ):
            list(serializers.deserialize("json", test_string))

    def test_helpful_error_message_invalid_field(self):
        """
        If there is an invalid field value, the error message should contain
        the model associated with it.
        """
        test_string = """[{
            "pk": "1",
            "model": "serializers.player",
            "fields": {
                "name": "Bob",
                "rank": "invalidint",
                "team": "Team"
            }
        }]"""
        expected = "(serializers.player:pk=1) field_value was 'invalidint'"
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("json", test_string))

    def test_helpful_error_message_for_foreign_keys(self):
        """
        Invalid foreign keys with a natural key should throw a helpful error
        message, such as what the failing key is.
        """
        test_string = """[{
            "pk": 1,
            "model": "serializers.category",
            "fields": {
                "name": "Unknown foreign key",
                "meta_data": [
                    "doesnotexist",
                    "metadata"
                ]
            }
        }]"""
        key = ["doesnotexist", "metadata"]
        expected = "(serializers.category:pk=1) field_value was '%r'" % key
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("json", test_string))

    def test_helpful_error_message_for_many2many_non_natural(self):
        """
        Invalid many-to-many keys should throw a helpful error message.
        """
        test_string = """[{
            "pk": 1,
            "model": "serializers.article",
            "fields": {
                "author": 1,
                "headline": "Unknown many to many",
                "pub_date": "2014-09-15T10:35:00",
                "categories": [1, "doesnotexist"]
            }
        }, {
            "pk": 1,
            "model": "serializers.author",
            "fields": {
                "name": "Agnes"
            }
        }, {
            "pk": 1,
            "model": "serializers.category",
            "fields": {
                "name": "Reference"
            }
        }]"""
        expected = "(serializers.article:pk=1) field_value was 'doesnotexist'"
        with self.assertRaisesMessage(DeserializationError, expected):
            list(serializers.deserialize("json", test_string))

    def test_helpful_error_message_for_many2many_natural1(self):
        """
        Invalid many-to-many keys should throw a helpful error message.
        This tests the code path where one of a list of natural keys is
        invalid.
        """
        test_string = """[{
            "pk": 1,
            "model": "serializers.categorymetadata",
            "fields": {
                "kind": "author",
                "name": "meta1",
                "value": "Agnes"
            }
        }, {
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
        }, {
            "pk": 1,
            "model": "serializers.author",
            "fields": {
                "name": "Agnes"
            }
        }]"""
        key = ["doesnotexist", "meta1"]
        expected = "(serializers.article:pk=1) field_value was '%r'" % key
        with self.assertRaisesMessage(DeserializationError, expected):
            for obj in serializers.deserialize("json", test_string):
                obj.save()

    def test_helpful_error_message_for_many2many_natural2(self):
        """
        Invalid many-to-many keys should throw a helpful error message. This
        tests the code path where a natural many-to-many key has only a single
        value.
        """
        test_string = """[{
            "pk": 1,
            "model": "serializers.article",
            "fields": {
                "author": 1,
                "headline": "Unknown many to many",
                "pub_date": "2014-09-15T10:35:00",
                "meta_data": [1, "doesnotexist"]
            }
        }, {
            "pk": 1,
            "model": "serializers.categorymetadata",
            "fields": {
                "kind": "author",
                "name": "meta1",
                "value": "Agnes"
            }
        }, {
            "pk": 1,
            "model": "serializers.author",
            "fields": {
                "name": "Agnes"
            }
        }]"""
        expected = "(serializers.article:pk=1) field_value was 'doesnotexist'"
        with self.assertRaisesMessage(DeserializationError, expected):
            for obj in serializers.deserialize("json", test_string, ignore=False):
                obj.save()

    def test_helpful_error_message_for_many2many_not_iterable(self):
        """
        Not iterable many-to-many field value throws a helpful error message.
        """
        test_string = """[{
            "pk": 1,
            "model": "serializers.m2mdata",
            "fields": {"data": null}
        }]"""

        expected = "(serializers.m2mdata:pk=1) field_value was 'None'"
        with self.assertRaisesMessage(DeserializationError, expected):
            next(serializers.deserialize("json", test_string, ignore=False))

    def test_m2m_natural_key_ordering(self):
        """
        M2M relations with natural keys are serialized in a deterministic order
        (by PK) when the model does not have a default ordering.
        """
        author = Author.objects.create(name="Jane Doe")
        a1 = Article.objects.create(
            headline="Test Article",
            pub_date=datetime.datetime(2025, 1, 1),
            author=author,
        )
        c1 = Category.objects.create(name="z_last")
        c2 = Category.objects.create(name="a_first")
        a1.categories.add(c1, c2)

        def fake_natural_key(self):
            return (self.name,)

        s = serializers.json.Serializer()
        with (
            mock.patch.object(Category, "natural_key", fake_natural_key, create=True),
            mock.patch.object(Category._meta, "ordering", []),
            mock.patch.object(
                models.QuerySet,
                "order_by",
                side_effect=models.QuerySet.order_by,
                autospec=True,
            ) as mock_order_by,
        ):

            output = s.serialize([a1], use_natural_foreign_keys=True)
            data = json.loads(output)
            m2m_data = data[0]["fields"]["categories"]
            self.assertEqual(m2m_data, [list(c1.natural_key()), list(c2.natural_key())])
            calls = [call.args for call in mock_order_by.call_args_list]
            self.assertTrue(
                any("pk" in args for args in calls),
                "QuerySet.order_by('pk') was not called.",
            )


class JsonSerializerTransactionTestCase(
    SerializersTransactionTestBase, TransactionTestCase
):
    serializer_name = "json"
    fwd_ref_str = """[
    {
        "pk": 1,
        "model": "serializers.article",
        "fields": {
            "headline": "Forward references pose no problem",
            "pub_date": "2006-06-16T15:00:00",
            "categories": [1],
            "author": 1
        }
    },
    {
        "pk": 1,
        "model": "serializers.category",
        "fields": {
            "name": "Reference"
        }
    },
    {
        "pk": 1,
        "model": "serializers.author",
        "fields": {
            "name": "Agnes"
        }
    }]"""


class DjangoJSONEncoderTests(SimpleTestCase):
    def test_lazy_string_encoding(self):
        self.assertEqual(
            json.dumps({"lang": gettext_lazy("French")}, cls=DjangoJSONEncoder),
            '{"lang": "French"}',
        )
        with override("fr"):
            self.assertEqual(
                json.dumps({"lang": gettext_lazy("French")}, cls=DjangoJSONEncoder),
                '{"lang": "Fran\\u00e7ais"}',
            )

    def test_timedelta(self):
        duration = datetime.timedelta(days=1, hours=2, seconds=3)
        self.assertEqual(
            json.dumps({"duration": duration}, cls=DjangoJSONEncoder),
            '{"duration": "P1DT02H00M03S"}',
        )
        duration = datetime.timedelta(0)
        self.assertEqual(
            json.dumps({"duration": duration}, cls=DjangoJSONEncoder),
            '{"duration": "P0DT00H00M00S"}',
        )
