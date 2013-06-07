# encoding: utf8
import datetime
from django.test import TransactionTestCase
from django.db.migrations.writer import MigrationWriter
from django.db import models, migrations


class WriterTests(TransactionTestCase):
    """
    Tests the migration writer (makes migration files from Migration instances)
    """

    def safe_exec(self, value, string):
        l = {}
        try:
            exec(string, {}, l)
        except:
            self.fail("Could not serialize %r: failed to exec %r" % (value, string.strip()))
        return l

    def assertSerializedEqual(self, value):
        string, imports = MigrationWriter.serialize(value)
        new_value = self.safe_exec(value, "%s\ntest_value_result = %s" % ("\n".join(imports), string))['test_value_result']
        self.assertEqual(new_value, value)

    def assertSerializedIs(self, value):
        string, imports = MigrationWriter.serialize(value)
        new_value = self.safe_exec(value, "%s\ntest_value_result = %s" % ("\n".join(imports), string))['test_value_result']
        self.assertIs(new_value, value)

    def test_serialize(self):
        """
        Tests various different forms of the serializer.
        This does not care about formatting, just that the parsed result is
        correct, so we always exec() the result and check that.
        """
        # Basic values
        self.assertSerializedEqual(1)
        self.assertSerializedEqual(None)
        self.assertSerializedEqual("foobar")
        self.assertSerializedEqual(u"föobár")
        self.assertSerializedEqual({1: 2})
        self.assertSerializedEqual(["a", 2, True, None])
        self.assertSerializedEqual(set([2, 3, "eighty"]))
        self.assertSerializedEqual({"lalalala": ["yeah", "no", "maybe"]})
        # Datetime stuff
        self.assertSerializedEqual(datetime.datetime.utcnow())
        self.assertSerializedEqual(datetime.datetime.utcnow)
        self.assertSerializedEqual(datetime.date.today())
        self.assertSerializedEqual(datetime.date.today)

    def test_simple_migration(self):
        """
        Tests serializing a simple migration.
        """
        migration = type("Migration", (migrations.Migration,), {
            "operations": [
                migrations.DeleteModel("MyModel"),
                migrations.AddField("OtherModel", "field_name", models.DateTimeField(default=datetime.datetime.utcnow))
            ],
            "dependencies": [("testapp", "some_other_one")],
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        print output
