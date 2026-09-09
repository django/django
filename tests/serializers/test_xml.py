from xml.dom import minidom

from django.core import serializers
from django.core.serializers.xml_serializer import DTDForbidden
from django.test import TestCase, TransactionTestCase

from .models import Actor
from .tests import SerializersTestBase, SerializersTransactionTestBase


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
    <field name="categories" rel="ManyToManyRel" to="serializers.category">
      <object pk="%(first_category_pk)s"></object>
      <object pk="%(second_category_pk)s"></object>
    </field>
    <field name="meta_data" rel="ManyToManyRel" to="serializers.categorymetadata"></field>
    <field name="topics" rel="ManyToManyRel" to="serializers.topic"></field>
  </object>
</django-objects>"""  # NOQA

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
        self.a1.headline = "HT \u0009, LF \u000a, and CR \u000d are allowed"
        self.assertIn(
            "HT \t, LF \n, and CR \r are allowed",
            serializers.serialize(self.serializer_name, [self.a1]),
        )

    def test_control_char_failure_attribute(self):
        actor = Actor.objects.create(pk="\u0001")
        msg = "Actor (pk:%s) contains unserializable characters" % actor.pk
        with self.assertRaisesMessage(ValueError, msg):
            serializers.serialize(self.serializer_name, [actor])

    def test_no_dtd(self):
        """
        The XML deserializer shouldn't allow a DTD.

        This is the most straightforward way to prevent all entity definitions
        and avoid both external entities and entity-expansion attacks.
        """
        xml = (
            '<?xml version="1.0" standalone="no"?>'
            '<!DOCTYPE example SYSTEM "http://example.com/example.dtd">'
        )
        with self.assertRaises(DTDForbidden):
            next(serializers.deserialize("xml", xml))

    def test_significant_whitespace_survives_round_trip(self):
        """
        Leading and trailing whitespace in a field value is preserved by a
        serialize/deserialize round trip.
        """
        self.a1.headline = "\tLeading and trailing  "
        serial_str = serializers.serialize(self.serializer_name, [self.a1])
        self.assertIn('xml:space="preserve"', serial_str)
        obj = next(serializers.deserialize(self.serializer_name, serial_str)).object
        self.assertEqual(obj.headline, "\tLeading and trailing  ")

    def test_whitespace_marker_omitted_when_not_needed(self):
        """xml:space is only emitted for values that need it."""
        self.a1.headline = "No surrounding whitespace"
        serial_str = serializers.serialize(self.serializer_name, [self.a1])
        self.assertNotIn("xml:space", serial_str)

    def test_field_text_without_marker_is_stripped(self):
        """
        Field text is still stripped when xml:space="preserve" is absent, so
        that hand-indented fixtures keep loading as intended.
        """
        xml = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
    <object model="serializers.category" pk="1">
        <field type="CharField" name="name">
            Reference
        </field>
    </object>
</django-objects>"""
        obj = next(serializers.deserialize(self.serializer_name, xml)).object
        self.assertEqual(obj.name, "Reference")


class XmlSerializerTransactionTestCase(
    SerializersTransactionTestBase, TransactionTestCase
):
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
</django-objects>"""  # NOQA
