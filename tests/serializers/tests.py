# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib
import json
import re
import unittest
from datetime import datetime
from xml.dom import minidom

from django.core import management, serializers
from django.core.serializers.base import ProgressBar
from django.db import connection, transaction
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, mock, override_settings,
    skipUnlessDBFeature,
)
from django.test.utils import Approximate
from django.utils import six
from django.utils.six import StringIO

from .models import (
    Actor, Article, Author, AuthorProfile, Category, Movie, Player, Score,
    Team,
)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@override_settings(
    SERIALIZATION_MODULES={
        "json2": "django.core.serializers.json",
    }
)
class SerializerRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.old_serializers = serializers._serializers
        serializers._serializers = {}

    def tearDown(self):
        serializers._serializers = self.old_serializers

    def test_register(self):
        "Registering a new serializer populates the full registry. Refs #14823"
        serializers.register_serializer('json3', 'django.core.serializers.json')

        public_formats = serializers.get_public_serializer_formats()
        self.assertIn('json3', public_formats)
        self.assertIn('json2', public_formats)
        self.assertIn('xml', public_formats)

    def test_unregister(self):
        "Unregistering a serializer doesn't cause the registry to be repopulated. Refs #14823"
        serializers.unregister_serializer('xml')
        serializers.register_serializer('json3', 'django.core.serializers.json')

        public_formats = serializers.get_public_serializer_formats()

        self.assertNotIn('xml', public_formats)
        self.assertIn('json3', public_formats)

    def test_builtin_serializers(self):
        "Requesting a list of serializer formats popuates the registry"
        all_formats = set(serializers.get_serializer_formats())
        public_formats = set(serializers.get_public_serializer_formats())

        self.assertIn('xml', all_formats),
        self.assertIn('xml', public_formats)

        self.assertIn('json2', all_formats)
        self.assertIn('json2', public_formats)

        self.assertIn('python', all_formats)
        self.assertNotIn('python', public_formats)


class SerializersTestBase(object):
    @staticmethod
    def _comparison_value(value):
        return value

    def setUp(self):
        sports = Category.objects.create(name="Sports")
        music = Category.objects.create(name="Music")
        op_ed = Category.objects.create(name="Op-Ed")

        self.joe = Author.objects.create(name="Joe")
        self.jane = Author.objects.create(name="Jane")

        self.a1 = Article(
            author=self.jane,
            headline="Poker has no place on ESPN",
            pub_date=datetime(2006, 6, 16, 11, 00)
        )
        self.a1.save()
        self.a1.categories = [sports, op_ed]

        self.a2 = Article(
            author=self.joe,
            headline="Time to reform copyright",
            pub_date=datetime(2006, 6, 16, 13, 00, 11, 345)
        )
        self.a2.save()
        self.a2.categories = [music, op_ed]

    def test_serialize(self):
        """Tests that basic serialization works."""
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        self.assertTrue(self._validate_output(serial_str))

    def test_serializer_roundtrip(self):
        """Tests that serialized content can be deserialized."""
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        models = list(serializers.deserialize(self.serializer_name, serial_str))
        self.assertEqual(len(models), 2)

    def test_altering_serialized_output(self):
        """
        Tests the ability to create new objects by
        modifying serialized content.
        """
        old_headline = "Poker has no place on ESPN"
        new_headline = "Poker has no place on television"
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        serial_str = serial_str.replace(old_headline, new_headline)
        models = list(serializers.deserialize(self.serializer_name, serial_str))

        # Prior to saving, old headline is in place
        self.assertTrue(Article.objects.filter(headline=old_headline))
        self.assertFalse(Article.objects.filter(headline=new_headline))

        for model in models:
            model.save()

        # After saving, new headline is in place
        self.assertTrue(Article.objects.filter(headline=new_headline))
        self.assertFalse(Article.objects.filter(headline=old_headline))

    def test_one_to_one_as_pk(self):
        """
        Tests that if you use your own primary key field
        (such as a OneToOneField), it doesn't appear in the
        serialized field list - it replaces the pk identifier.
        """
        profile = AuthorProfile(author=self.joe,
                                date_of_birth=datetime(1970, 1, 1))
        profile.save()
        serial_str = serializers.serialize(self.serializer_name,
                                           AuthorProfile.objects.all())
        self.assertFalse(self._get_field_values(serial_str, 'author'))

        for obj in serializers.deserialize(self.serializer_name, serial_str):
            self.assertEqual(obj.object.pk, self._comparison_value(self.joe.pk))

    def test_serialize_field_subset(self):
        """Tests that output can be restricted to a subset of fields"""
        valid_fields = ('headline', 'pub_date')
        invalid_fields = ("author", "categories")
        serial_str = serializers.serialize(self.serializer_name,
                                    Article.objects.all(),
                                    fields=valid_fields)
        for field_name in invalid_fields:
            self.assertFalse(self._get_field_values(serial_str, field_name))

        for field_name in valid_fields:
            self.assertTrue(self._get_field_values(serial_str, field_name))

    def test_serialize_unicode(self):
        """Tests that unicode makes the roundtrip intact"""
        actor_name = "Za\u017c\u00f3\u0142\u0107"
        movie_title = 'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = serializers.serialize(self.serializer_name, [mv])
        self.assertEqual(self._get_field_values(serial_str, "title")[0], movie_title)
        self.assertEqual(self._get_field_values(serial_str, "actor")[0], actor_name)

        obj_list = list(serializers.deserialize(self.serializer_name, serial_str))
        mv_obj = obj_list[0].object
        self.assertEqual(mv_obj.title, movie_title)

    def test_serialize_progressbar(self):
        fake_stdout = StringIO()
        serializers.serialize(
            self.serializer_name, Article.objects.all(),
            progress_output=fake_stdout, object_count=Article.objects.count()
        )
        self.assertTrue(
            fake_stdout.getvalue().endswith('[' + '.' * ProgressBar.progress_width + ']\n')
        )

    def test_serialize_superfluous_queries(self):
        """Ensure no superfluous queries are made when serializing ForeignKeys

        #17602
        """
        ac = Actor(name='Actor name')
        ac.save()
        mv = Movie(title='Movie title', actor_id=ac.pk)
        mv.save()

        with self.assertNumQueries(0):
            serializers.serialize(self.serializer_name, [mv])

    def test_serialize_with_null_pk(self):
        """
        Tests that serialized data with no primary key results
        in a model instance with no id
        """
        category = Category(name="Reference")
        serial_str = serializers.serialize(self.serializer_name, [category])
        pk_value = self._get_pk_values(serial_str)[0]
        self.assertFalse(pk_value)

        cat_obj = list(serializers.deserialize(self.serializer_name,
                                               serial_str))[0].object
        self.assertEqual(cat_obj.id, None)

    def test_float_serialization(self):
        """Tests that float values serialize and deserialize intact"""
        sc = Score(score=3.4)
        sc.save()
        serial_str = serializers.serialize(self.serializer_name, [sc])
        deserial_objs = list(serializers.deserialize(self.serializer_name,
                                                serial_str))
        self.assertEqual(deserial_objs[0].object.score, Approximate(3.4, places=1))

    def test_deferred_field_serialization(self):
        author = Author.objects.create(name='Victor Hugo')
        author = Author.objects.defer('name').get(pk=author.pk)
        serial_str = serializers.serialize(self.serializer_name, [author])
        deserial_objs = list(serializers.deserialize(self.serializer_name, serial_str))
        # Check the class instead of using isinstance() because model instances
        # with deferred fields (e.g. Author_Deferred_name) will pass isinstance.
        self.assertEqual(deserial_objs[0].object.__class__, Author)

    def test_custom_field_serialization(self):
        """Tests that custom fields serialize and deserialize intact"""
        team_str = "Spartak Moskva"
        player = Player()
        player.name = "Soslan Djanaev"
        player.rank = 1
        player.team = Team(team_str)
        player.save()
        serial_str = serializers.serialize(self.serializer_name,
                                           Player.objects.all())
        team = self._get_field_values(serial_str, "team")
        self.assertTrue(team)
        self.assertEqual(team[0], team_str)

        deserial_objs = list(serializers.deserialize(self.serializer_name, serial_str))
        self.assertEqual(deserial_objs[0].object.team.to_string(),
                         player.team.to_string())

    def test_pre_1000ad_date(self):
        """Tests that year values before 1000AD are properly formatted"""
        # Regression for #12524 -- dates before 1000AD get prefixed
        # 0's on the year
        a = Article.objects.create(
            author=self.jane,
            headline="Nobody remembers the early years",
            pub_date=datetime(1, 2, 3, 4, 5, 6))

        serial_str = serializers.serialize(self.serializer_name, [a])
        date_values = self._get_field_values(serial_str, "pub_date")
        self.assertEqual(date_values[0].replace('T', ' '), "0001-02-03 04:05:06")

    def test_pkless_serialized_strings(self):
        """
        Tests that serialized strings without PKs
        can be turned into models
        """
        deserial_objs = list(serializers.deserialize(self.serializer_name,
                                                     self.pkless_str))
        for obj in deserial_objs:
            self.assertFalse(obj.object.id)
            obj.save()
        self.assertEqual(Category.objects.all().count(), 5)

    def test_deterministic_mapping_ordering(self):
        """Mapping such as fields should be deterministically ordered. (#24558)"""
        output = serializers.serialize(self.serializer_name, [self.a1], indent=2)
        categories = self.a1.categories.values_list('pk', flat=True)
        self.assertEqual(output, self.mapping_ordering_str % {
            'article_pk': self.a1.pk,
            'author_pk': self.a1.author_id,
            'first_category_pk': categories[0],
            'second_category_pk': categories[1],
        })

    def test_deserialize_force_insert(self):
        """Tests that deserialized content can be saved with force_insert as a parameter."""
        serial_str = serializers.serialize(self.serializer_name, [self.a1])
        deserial_obj = list(serializers.deserialize(self.serializer_name, serial_str))[0]
        with mock.patch('django.db.models.Model') as mock_model:
            deserial_obj.save(force_insert=False)
            mock_model.save_base.assert_called_with(deserial_obj.object, raw=True, using=None, force_insert=False)


class SerializersTransactionTestBase(object):

    available_apps = ['serializers']

    @skipUnlessDBFeature('supports_forward_references')
    def test_forward_refs(self):
        """
        Tests that objects ids can be referenced before they are
        defined in the serialization data.
        """
        # The deserialization process needs to run in a transaction in order
        # to test forward reference handling.
        with transaction.atomic():
            objs = serializers.deserialize(self.serializer_name, self.fwd_ref_str)
            with connection.constraint_checks_disabled():
                for obj in objs:
                    obj.save()

        for model_cls in (Category, Author, Article):
            self.assertEqual(model_cls.objects.all().count(), 1)
        art_obj = Article.objects.all()[0]
        self.assertEqual(art_obj.categories.all().count(), 1)
        self.assertEqual(art_obj.author.name, "Agnes")


class XmlSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "xml"
    pkless_str = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
    <object model="serializers.category">
        <field type="CharField" name="name">Reference</field>
    </object>
    <object model="serializers.category">
        <field type="CharField" name="name">Non-fiction</field>
    </object>
</django-objects>"""
    mapping_ordering_str = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serializers.article" pk="%(article_pk)s">
    <field name="author" rel="ManyToOneRel" to="serializers.author">%(author_pk)s</field>
    <field name="headline" type="CharField">Poker has no place on ESPN</field>
    <field name="pub_date" type="DateTimeField">2006-06-16T11:00:00</field>
    <field name="categories" rel="ManyToManyRel" to="serializers.category"><object pk="%(first_category_pk)s"></object><object pk="%(second_category_pk)s"></object></field>
    <field name="meta_data" rel="ManyToManyRel" to="serializers.categorymetadata"></field>
  </object>
</django-objects>"""

    @staticmethod
    def _comparison_value(value):
        # The XML serializer handles everything as strings, so comparisons
        # need to be performed on the stringified value
        return six.text_type(value)

    @staticmethod
    def _validate_output(serial_str):
        try:
            minidom.parseString(serial_str)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        ret_list = []
        dom = minidom.parseString(serial_str)
        fields = dom.getElementsByTagName("object")
        for field in fields:
            ret_list.append(field.getAttribute("pk"))
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        dom = minidom.parseString(serial_str)
        fields = dom.getElementsByTagName("field")
        for field in fields:
            if field.getAttribute("name") == field_name:
                temp = []
                for child in field.childNodes:
                    temp.append(child.nodeValue)
                ret_list.append("".join(temp))
        return ret_list

    def test_control_char_failure(self):
        """
        Serializing control characters with XML should fail as those characters
        are not supported in the XML 1.0 standard (except HT, LF, CR).
        """
        self.a1.headline = "This contains \u0001 control \u0011 chars"
        msg = "Article.headline (pk:%s) contains unserializable characters" % self.a1.pk
        with self.assertRaisesMessage(ValueError, msg):
            serializers.serialize(self.serializer_name, [self.a1])
        self.a1.headline = "HT \u0009, LF \u000A, and CR \u000D are allowed"
        self.assertIn(
            "HT \t, LF \n, and CR \r are allowed",
            serializers.serialize(self.serializer_name, [self.a1])
        )


class XmlSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
    serializer_name = "xml"
    fwd_ref_str = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
    <object pk="1" model="serializers.article">
        <field to="serializers.author" name="author" rel="ManyToOneRel">1</field>
        <field type="CharField" name="headline">Forward references pose no problem</field>
        <field type="DateTimeField" name="pub_date">2006-06-16T15:00:00</field>
        <field to="serializers.category" name="categories" rel="ManyToManyRel">
            <object pk="1"></object>
        </field>
        <field to="serializers.categorymetadata" name="meta_data" rel="ManyToManyRel"></field>
    </object>
    <object pk="1" model="serializers.author">
        <field type="CharField" name="name">Agnes</field>
    </object>
    <object pk="1" model="serializers.category">
        <field type="CharField" name="name">Reference</field></object>
</django-objects>"""


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
    "meta_data": []
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
        ret_list = []
        serial_list = json.loads(serial_str)
        for obj_dict in serial_list:
            ret_list.append(obj_dict["pk"])
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        serial_list = json.loads(serial_str)
        for obj_dict in serial_list:
            if field_name in obj_dict["fields"]:
                ret_list.append(obj_dict["fields"][field_name])
        return ret_list

    def test_indentation_whitespace(self):
        Score.objects.create(score=5.0)
        Score.objects.create(score=6.0)
        qset = Score.objects.all()

        s = serializers.json.Serializer()
        json_data = s.serialize(qset, indent=2)
        for line in json_data.splitlines():
            if re.search(r'.+,\s*$', line):
                self.assertEqual(line, line.rstrip())

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
        with self.assertRaisesMessage(serializers.base.DeserializationError, "(serializers.player:pk=badpk)"):
            list(serializers.deserialize('json', test_string))

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
        with self.assertRaisesMessage(serializers.base.DeserializationError, expected):
            list(serializers.deserialize('json', test_string))

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
        with self.assertRaisesMessage(serializers.base.DeserializationError, expected):
            list(serializers.deserialize('json', test_string))

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
        with self.assertRaisesMessage(serializers.base.DeserializationError, expected):
            list(serializers.deserialize('json', test_string))

    def test_helpful_error_message_for_many2many_natural1(self):
        """
        Invalid many-to-many keys should throw a helpful error message.
        This tests the code path where one of a list of natural keys is invalid.
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
        with self.assertRaisesMessage(serializers.base.DeserializationError, expected):
            for obj in serializers.deserialize('json', test_string):
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
        with self.assertRaisesMessage(serializers.base.DeserializationError, expected):
            for obj in serializers.deserialize('json', test_string, ignore=False):
                obj.save()


class JsonSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
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


YAML_IMPORT_ERROR_MESSAGE = r'No module named yaml'


class YamlImportModuleMock(object):
    """Provides a wrapped import_module function to simulate yaml ImportError

    In order to run tests that verify the behavior of the YAML serializer
    when run on a system that has yaml installed (like the django CI server),
    mock import_module, so that it raises an ImportError when the yaml
    serializer is being imported.  The importlib.import_module() call is
    being made in the serializers.register_serializer().

    Refs: #12756
    """
    def __init__(self):
        self._import_module = importlib.import_module

    def import_module(self, module_path):
        if module_path == serializers.BUILTIN_SERIALIZERS['yaml']:
            raise ImportError(YAML_IMPORT_ERROR_MESSAGE)

        return self._import_module(module_path)


class NoYamlSerializerTestCase(SimpleTestCase):
    """Not having pyyaml installed provides a misleading error

    Refs: #12756
    """
    @classmethod
    def setUpClass(cls):
        """Removes imported yaml and stubs importlib.import_module"""
        super(NoYamlSerializerTestCase, cls).setUpClass()

        cls._import_module_mock = YamlImportModuleMock()
        importlib.import_module = cls._import_module_mock.import_module

        # clear out cached serializers to emulate yaml missing
        serializers._serializers = {}

    @classmethod
    def tearDownClass(cls):
        """Puts yaml back if necessary"""
        super(NoYamlSerializerTestCase, cls).tearDownClass()

        importlib.import_module = cls._import_module_mock._import_module

        # clear out cached serializers to clean out BadSerializer instances
        serializers._serializers = {}

    def test_serializer_pyyaml_error_message(self):
        """Using yaml serializer without pyyaml raises ImportError"""
        jane = Author(name="Jane")
        self.assertRaises(ImportError, serializers.serialize, "yaml", [jane])

    def test_deserializer_pyyaml_error_message(self):
        """Using yaml deserializer without pyyaml raises ImportError"""
        self.assertRaises(ImportError, serializers.deserialize, "yaml", "")

    def test_dumpdata_pyyaml_error_message(self):
        """Calling dumpdata produces an error when yaml package missing"""
        with six.assertRaisesRegex(self, management.CommandError, YAML_IMPORT_ERROR_MESSAGE):
            management.call_command('dumpdata', format='yaml')


@unittest.skipUnless(HAS_YAML, "No yaml library detected")
class YamlSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "yaml"
    fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: serializers.article
- fields:
    name: Reference
  pk: 1
  model: serializers.category
- fields:
    name: Agnes
  pk: 1
  model: serializers.author"""

    pkless_str = """- fields:
    name: Reference
  pk: null
  model: serializers.category
- fields:
    name: Non-fiction
  model: serializers.category"""

    mapping_ordering_str = """- model: serializers.article
  pk: %(article_pk)s
  fields:
    author: %(author_pk)s
    headline: Poker has no place on ESPN
    pub_date: 2006-06-16 11:00:00
    categories: [%(first_category_pk)s, %(second_category_pk)s]
    meta_data: []
"""

    @staticmethod
    def _validate_output(serial_str):
        try:
            yaml.safe_load(StringIO(serial_str))
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        ret_list = []
        stream = StringIO(serial_str)
        for obj_dict in yaml.safe_load(stream):
            ret_list.append(obj_dict["pk"])
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        stream = StringIO(serial_str)
        for obj_dict in yaml.safe_load(stream):
            if "fields" in obj_dict and field_name in obj_dict["fields"]:
                field_value = obj_dict["fields"][field_name]
                # yaml.safe_load will return non-string objects for some
                # of the fields we are interested in, this ensures that
                # everything comes back as a string
                if isinstance(field_value, six.string_types):
                    ret_list.append(field_value)
                else:
                    ret_list.append(str(field_value))
        return ret_list


@unittest.skipUnless(HAS_YAML, "No yaml library detected")
class YamlSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
    serializer_name = "yaml"
    fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: serializers.article
- fields:
    name: Reference
  pk: 1
  model: serializers.category
- fields:
    name: Agnes
  pk: 1
  model: serializers.author"""
