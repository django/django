# encoding: utf8

from __future__ import unicode_literals

import datetime

from django.utils import six
from django.test import TestCase
from django.db.migrations.writer import MigrationWriter
from django.db import models, migrations
from django.utils.translation import ugettext_lazy as _


class WriterTests(TestCase):
    """
    Tests the migration writer (makes migration files from Migration instances)
    """

    def safe_exec(self, string, value=None):
        l = {}
        try:
            exec(string, globals(), l)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return l

    def serialize_round_trip(self, value):
        string, imports = MigrationWriter.serialize(value)
        return self.safe_exec("%s\ntest_value_result = %s" % ("\n".join(imports), string), value)['test_value_result']

    def assertSerializedEqual(self, value):
        self.assertEqual(self.serialize_round_trip(value), value)

    def assertSerializedIs(self, value):
        self.assertIs(self.serialize_round_trip(value), value)

    def assertSerializedFieldEqual(self, value):
        new_value = self.serialize_round_trip(value)
        self.assertEqual(value.__class__, new_value.__class__)
        self.assertEqual(value.max_length, new_value.max_length)
        self.assertEqual(value.null, new_value.null)
        self.assertEqual(value.unique, new_value.unique)

    def test_serialize(self):
        """
        Tests various different forms of the serializer.
        This does not care about formatting, just that the parsed result is
        correct, so we always exec() the result and check that.
        """
        # Basic values
        self.assertSerializedEqual(1)
        self.assertSerializedEqual(None)
        self.assertSerializedEqual(b"foobar")
        self.assertSerializedEqual("föobár")
        self.assertSerializedEqual({1: 2})
        self.assertSerializedEqual(["a", 2, True, None])
        self.assertSerializedEqual(set([2, 3, "eighty"]))
        self.assertSerializedEqual({"lalalala": ["yeah", "no", "maybe"]})
        self.assertSerializedEqual(_('Hello'))
        # Functions
        with six.assertRaisesRegex(self, ValueError, 'Cannot serialize function: lambda'):
            self.assertSerializedEqual(lambda x: 42)
        self.assertSerializedEqual(models.SET_NULL)
        string, imports = MigrationWriter.serialize(models.SET(42))
        self.assertEqual(string, 'models.SET(42)')
        self.serialize_round_trip(models.SET(42))
        # Datetime stuff
        self.assertSerializedEqual(datetime.datetime.utcnow())
        self.assertSerializedEqual(datetime.datetime.utcnow)
        self.assertSerializedEqual(datetime.date.today())
        self.assertSerializedEqual(datetime.date.today)
        # Django fields
        self.assertSerializedFieldEqual(models.CharField(max_length=255))
        self.assertSerializedFieldEqual(models.TextField(null=True, blank=True))

    def test_simple_migration(self):
        """
        Tests serializing a simple migration.
        """
        migration = type(str("Migration"), (migrations.Migration,), {
            "operations": [
                migrations.DeleteModel("MyModel"),
                migrations.AddField("OtherModel", "field_name", models.DateTimeField(default=datetime.datetime.utcnow))
            ],
            "dependencies": [("testapp", "some_other_one")],
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        # It should NOT be unicode.
        self.assertIsInstance(output, six.binary_type, "Migration as_string returned unicode")
        # We don't test the output formatting - that's too fragile.
        # Just make sure it runs for now, and that things look alright.
        result = self.safe_exec(output)
        self.assertIn("Migration", result)
