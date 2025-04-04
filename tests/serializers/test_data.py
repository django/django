"""
A test spanning all the capabilities of all the serializers.

This class defines sample data and a dynamically generated
test case that is capable of testing the capabilities of
the serializers. This includes all valid data values, plus
forward, backwards and self references.
"""

import datetime
import decimal
import uuid
from collections import namedtuple

from django.core import serializers
from django.db import connection, models
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import (
    Anchor,
    AutoNowDateTimeData,
    BigIntegerData,
    BinaryData,
    BooleanData,
    BooleanPKData,
    CharData,
    CharPKData,
    DateData,
    DatePKData,
    DateTimeData,
    DateTimePKData,
    DecimalData,
    DecimalPKData,
    EmailData,
    EmailPKData,
    ExplicitInheritBaseModel,
    FileData,
    FilePathData,
    FilePathPKData,
    FKData,
    FKDataToField,
    FKDataToO2O,
    FKSelfData,
    FKToUUID,
    FloatData,
    FloatPKData,
    GenericData,
    GenericIPAddressData,
    GenericIPAddressPKData,
    InheritAbstractModel,
    InheritBaseModel,
    IntegerData,
    IntegerPKData,
    Intermediate,
    LengthModel,
    M2MData,
    M2MIntermediateData,
    M2MSelfData,
    ModifyingSaveData,
    O2OData,
    PositiveBigIntegerData,
    PositiveIntegerData,
    PositiveIntegerPKData,
    PositiveSmallIntegerData,
    PositiveSmallIntegerPKData,
    SlugData,
    SlugPKData,
    SmallData,
    SmallPKData,
    Tag,
    TextData,
    TextPKData,
    TimeData,
    TimePKData,
    UniqueAnchor,
    UUIDData,
    UUIDDefaultData,
)
from .tests import register_tests

# A set of functions that can be used to recreate
# test data objects of various kinds.
# The save method is a raw base model save, to make
# sure that the data in the database matches the
# exact test case.


def data_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data
    models.Model.save_base(instance, raw=True)
    return [instance]


def generic_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data[0]
    models.Model.save_base(instance, raw=True)
    for tag in data[1:]:
        instance.tags.create(data=tag)
    return [instance]


def fk_create(pk, klass, data):
    instance = klass(id=pk)
    setattr(instance, "data_id", data)
    models.Model.save_base(instance, raw=True)
    return [instance]


def m2m_create(pk, klass, data):
    instance = klass(id=pk)
    models.Model.save_base(instance, raw=True)
    instance.data.set(data)
    return [instance]


def im2m_create(pk, klass, data):
    instance = klass(id=pk)
    models.Model.save_base(instance, raw=True)
    return [instance]


def im_create(pk, klass, data):
    instance = klass(id=pk)
    instance.right_id = data["right"]
    instance.left_id = data["left"]
    if "extra" in data:
        instance.extra = data["extra"]
    models.Model.save_base(instance, raw=True)
    return [instance]


def o2o_create(pk, klass, data):
    instance = klass()
    instance.data_id = data
    models.Model.save_base(instance, raw=True)
    return [instance]


def pk_create(pk, klass, data):
    instance = klass()
    instance.data = data
    models.Model.save_base(instance, raw=True)
    return [instance]


def inherited_create(pk, klass, data):
    instance = klass(id=pk, **data)
    # This isn't a raw save because:
    #  1) we're testing inheritance, not field behavior, so none
    #     of the field values need to be protected.
    #  2) saving the child class and having the parent created
    #     automatically is easier than manually creating both.
    models.Model.save(instance)
    created = [instance]
    for klass in instance._meta.parents:
        created.append(klass.objects.get(id=pk))
    return created


# A set of functions that can be used to compare
# test data objects of various kinds


def data_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    if klass == BinaryData and data is not None:
        testcase.assertEqual(
            bytes(data),
            bytes(instance.data),
            "Objects with PK=%d not equal; expected '%s' (%s), got '%s' (%s)"
            % (
                pk,
                repr(bytes(data)),
                type(data),
                repr(bytes(instance.data)),
                type(instance.data),
            ),
        )
    else:
        testcase.assertEqual(
            data,
            instance.data,
            "Objects with PK=%d not equal; expected '%s' (%s), got '%s' (%s)"
            % (
                pk,
                data,
                type(data),
                instance,
                type(instance.data),
            ),
        )


def generic_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data[0], instance.data)
    testcase.assertEqual(data[1:], [t.data for t in instance.tags.order_by("id")])


def fk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, instance.data_id)


def m2m_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, [obj.id for obj in instance.data.order_by("id")])


def im2m_compare(testcase, pk, klass, data):
    klass.objects.get(id=pk)
    # actually nothing else to check, the instance just should exist


def im_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data["left"], instance.left_id)
    testcase.assertEqual(data["right"], instance.right_id)
    if "extra" in data:
        testcase.assertEqual(data["extra"], instance.extra)
    else:
        testcase.assertEqual("doesn't matter", instance.extra)


def o2o_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data_id)


def pk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data)


def inherited_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    for key, value in data.items():
        testcase.assertEqual(value, getattr(instance, key))


# Define some test helpers. Each has a pair of functions: one to create objects and one
# to make assertions against objects of a particular type.
TestHelper = namedtuple("TestHelper", ["create_object", "compare_object"])
data_obj = TestHelper(data_create, data_compare)
generic_obj = TestHelper(generic_create, generic_compare)
fk_obj = TestHelper(fk_create, fk_compare)
m2m_obj = TestHelper(m2m_create, m2m_compare)
im2m_obj = TestHelper(im2m_create, im2m_compare)
im_obj = TestHelper(im_create, im_compare)
o2o_obj = TestHelper(o2o_create, o2o_compare)
pk_obj = TestHelper(pk_create, pk_compare)
inherited_obj = TestHelper(inherited_create, inherited_compare)
uuid_obj = uuid.uuid4()

test_data = [
    # Format: (test helper, PK value, Model Class, data)
    (data_obj, 1, BinaryData, memoryview(b"\x05\xFD\x00")),
    (data_obj, 5, BooleanData, True),
    (data_obj, 6, BooleanData, False),
    (data_obj, 7, BooleanData, None),
    (data_obj, 10, CharData, "Test Char Data"),
    (data_obj, 11, CharData, ""),
    (data_obj, 12, CharData, "None"),
    (data_obj, 13, CharData, "null"),
    (data_obj, 14, CharData, "NULL"),
    # (We use something that will fit into a latin1 database encoding here,
    # because that is still the default used on many system setups.)
    (data_obj, 16, CharData, "\xa5"),
    (data_obj, 20, DateData, datetime.date(2006, 6, 16)),
    (data_obj, 21, DateData, None),
    (data_obj, 30, DateTimeData, datetime.datetime(2006, 6, 16, 10, 42, 37)),
    (data_obj, 31, DateTimeData, None),
    (data_obj, 40, EmailData, "hovercraft@example.com"),
    (data_obj, 42, EmailData, ""),
    (data_obj, 50, FileData, "file:///foo/bar/whiz.txt"),
    # (data_obj, 51, FileData, None),
    (data_obj, 52, FileData, ""),
    (data_obj, 60, FilePathData, "/foo/bar/whiz.txt"),
    (data_obj, 62, FilePathData, ""),
    (data_obj, 70, DecimalData, decimal.Decimal("12.345")),
    (data_obj, 71, DecimalData, decimal.Decimal("-12.345")),
    (data_obj, 72, DecimalData, decimal.Decimal("0.0")),
    (data_obj, 73, DecimalData, None),
    (data_obj, 74, FloatData, 12.345),
    (data_obj, 75, FloatData, -12.345),
    (data_obj, 76, FloatData, 0.0),
    (data_obj, 77, FloatData, None),
    (data_obj, 80, IntegerData, 123456789),
    (data_obj, 81, IntegerData, -123456789),
    (data_obj, 82, IntegerData, 0),
    (data_obj, 83, IntegerData, None),
    # (XX, ImageData
    (data_obj, 95, GenericIPAddressData, "fe80:1424:2223:6cff:fe8a:2e8a:2151:abcd"),
    (data_obj, 96, GenericIPAddressData, None),
    (data_obj, 110, PositiveBigIntegerData, 9223372036854775807),
    (data_obj, 111, PositiveBigIntegerData, None),
    (data_obj, 120, PositiveIntegerData, 123456789),
    (data_obj, 121, PositiveIntegerData, None),
    (data_obj, 130, PositiveSmallIntegerData, 12),
    (data_obj, 131, PositiveSmallIntegerData, None),
    (data_obj, 140, SlugData, "this-is-a-slug"),
    (data_obj, 142, SlugData, ""),
    (data_obj, 150, SmallData, 12),
    (data_obj, 151, SmallData, -12),
    (data_obj, 152, SmallData, 0),
    (data_obj, 153, SmallData, None),
    (
        data_obj,
        160,
        TextData,
        """This is a long piece of text.
It contains line breaks.
Several of them.
The end.""",
    ),
    (data_obj, 161, TextData, ""),
    (data_obj, 170, TimeData, datetime.time(10, 42, 37)),
    (data_obj, 171, TimeData, None),
    (generic_obj, 200, GenericData, ["Generic Object 1", "tag1", "tag2"]),
    (generic_obj, 201, GenericData, ["Generic Object 2", "tag2", "tag3"]),
    (data_obj, 300, Anchor, "Anchor 1"),
    (data_obj, 301, Anchor, "Anchor 2"),
    (data_obj, 302, UniqueAnchor, "UAnchor 1"),
    (fk_obj, 400, FKData, 300),  # Post reference
    (fk_obj, 401, FKData, 500),  # Pre reference
    (fk_obj, 402, FKData, None),  # Empty reference
    (m2m_obj, 410, M2MData, []),  # Empty set
    (m2m_obj, 411, M2MData, [300, 301]),  # Post reference
    (m2m_obj, 412, M2MData, [500, 501]),  # Pre reference
    (m2m_obj, 413, M2MData, [300, 301, 500, 501]),  # Pre and Post reference
    (o2o_obj, None, O2OData, 300),  # Post reference
    (o2o_obj, None, O2OData, 500),  # Pre reference
    (fk_obj, 430, FKSelfData, 431),  # Pre reference
    (fk_obj, 431, FKSelfData, 430),  # Post reference
    (fk_obj, 432, FKSelfData, None),  # Empty reference
    (m2m_obj, 440, M2MSelfData, []),
    (m2m_obj, 441, M2MSelfData, []),
    (m2m_obj, 442, M2MSelfData, [440, 441]),
    (m2m_obj, 443, M2MSelfData, [445, 446]),
    (m2m_obj, 444, M2MSelfData, [440, 441, 445, 446]),
    (m2m_obj, 445, M2MSelfData, []),
    (m2m_obj, 446, M2MSelfData, []),
    (fk_obj, 450, FKDataToField, "UAnchor 1"),
    (fk_obj, 451, FKDataToField, "UAnchor 2"),
    (fk_obj, 452, FKDataToField, None),
    (fk_obj, 460, FKDataToO2O, 300),
    (im2m_obj, 470, M2MIntermediateData, None),
    # testing post- and pre-references and extra fields
    (im_obj, 480, Intermediate, {"right": 300, "left": 470}),
    (im_obj, 481, Intermediate, {"right": 300, "left": 490}),
    (im_obj, 482, Intermediate, {"right": 500, "left": 470}),
    (im_obj, 483, Intermediate, {"right": 500, "left": 490}),
    (im_obj, 484, Intermediate, {"right": 300, "left": 470, "extra": "extra"}),
    (im_obj, 485, Intermediate, {"right": 300, "left": 490, "extra": "extra"}),
    (im_obj, 486, Intermediate, {"right": 500, "left": 470, "extra": "extra"}),
    (im_obj, 487, Intermediate, {"right": 500, "left": 490, "extra": "extra"}),
    (im2m_obj, 490, M2MIntermediateData, []),
    (data_obj, 500, Anchor, "Anchor 3"),
    (data_obj, 501, Anchor, "Anchor 4"),
    (data_obj, 502, UniqueAnchor, "UAnchor 2"),
    (pk_obj, 601, BooleanPKData, True),
    (pk_obj, 602, BooleanPKData, False),
    (pk_obj, 610, CharPKData, "Test Char PKData"),
    (pk_obj, 620, DatePKData, datetime.date(2006, 6, 16)),
    (pk_obj, 630, DateTimePKData, datetime.datetime(2006, 6, 16, 10, 42, 37)),
    (pk_obj, 640, EmailPKData, "hovercraft@example.com"),
    (pk_obj, 660, FilePathPKData, "/foo/bar/whiz.txt"),
    (pk_obj, 670, DecimalPKData, decimal.Decimal("12.345")),
    (pk_obj, 671, DecimalPKData, decimal.Decimal("-12.345")),
    (pk_obj, 672, DecimalPKData, decimal.Decimal("0.0")),
    (pk_obj, 673, FloatPKData, 12.345),
    (pk_obj, 674, FloatPKData, -12.345),
    (pk_obj, 675, FloatPKData, 0.0),
    (pk_obj, 680, IntegerPKData, 123456789),
    (pk_obj, 681, IntegerPKData, -123456789),
    (pk_obj, 682, IntegerPKData, 0),
    (pk_obj, 695, GenericIPAddressPKData, "fe80:1424:2223:6cff:fe8a:2e8a:2151:abcd"),
    (pk_obj, 720, PositiveIntegerPKData, 123456789),
    (pk_obj, 730, PositiveSmallIntegerPKData, 12),
    (pk_obj, 740, SlugPKData, "this-is-a-slug"),
    (pk_obj, 750, SmallPKData, 12),
    (pk_obj, 751, SmallPKData, -12),
    (pk_obj, 752, SmallPKData, 0),
    (pk_obj, 770, TimePKData, datetime.time(10, 42, 37)),
    (pk_obj, 791, UUIDData, uuid_obj),
    (fk_obj, 792, FKToUUID, uuid_obj),
    (pk_obj, 793, UUIDDefaultData, uuid_obj),
    (data_obj, 800, AutoNowDateTimeData, datetime.datetime(2006, 6, 16, 10, 42, 37)),
    (data_obj, 810, ModifyingSaveData, 42),
    (inherited_obj, 900, InheritAbstractModel, {"child_data": 37, "parent_data": 42}),
    (
        inherited_obj,
        910,
        ExplicitInheritBaseModel,
        {"child_data": 37, "parent_data": 42},
    ),
    (inherited_obj, 920, InheritBaseModel, {"child_data": 37, "parent_data": 42}),
    (data_obj, 1000, BigIntegerData, 9223372036854775807),
    (data_obj, 1001, BigIntegerData, -9223372036854775808),
    (data_obj, 1002, BigIntegerData, 0),
    (data_obj, 1003, BigIntegerData, None),
    (data_obj, 1004, LengthModel, 0),
    (data_obj, 1005, LengthModel, 1),
]


class SerializerDataTests(TestCase):
    pass


def assert_serializer(self, format, data):
    # Create all the objects defined in the test data.
    objects = []
    for test_helper, pk, model, data_value in data:
        with connection.constraint_checks_disabled():
            objects.extend(test_helper.create_object(pk, model, data_value))

    # Get a count of the number of objects created for each model class.
    instance_counts = {}
    for _, _, model, _ in data:
        if model not in instance_counts:
            instance_counts[model] = model.objects.count()

    # Add the generic tagged objects to the object list.
    objects.extend(Tag.objects.all())

    # Serialize the test database.
    serialized_data = serializers.serialize(format, objects, indent=2)

    for obj in serializers.deserialize(format, serialized_data):
        obj.save()

    # Assert that the deserialized data is the same as the original source.
    for test_helper, pk, model, data_value in data:
        with self.subTest(model=model, data_value=data_value):
            test_helper.compare_object(self, pk, model, data_value)

    # Assert no new objects were created.
    for model, count in instance_counts.items():
        with self.subTest(model=model, count=count):
            self.assertEqual(count, model.objects.count())


def serializerTest(self, format):
    assert_serializer(self, format, test_data)


@skipUnlessDBFeature("allows_auto_pk_0")
def serializerTestPK0(self, format):
    # FK to an object with PK of 0. This won't work on MySQL without the
    # NO_AUTO_VALUE_ON_ZERO SQL mode since it won't let you create an object
    # with an autoincrement primary key of 0.
    data = [
        (data_obj, 0, Anchor, "Anchor 0"),
        (fk_obj, 1, FKData, 0),
    ]
    assert_serializer(self, format, data)


@skipIfDBFeature("interprets_empty_strings_as_nulls")
def serializerTestNullValueStingField(self, format):
    data = [
        (data_obj, 1, BinaryData, None),
        (data_obj, 2, CharData, None),
        (data_obj, 3, EmailData, None),
        (data_obj, 4, FilePathData, None),
        (data_obj, 5, SlugData, None),
        (data_obj, 6, TextData, None),
    ]
    assert_serializer(self, format, data)


@skipUnlessDBFeature("supports_index_on_text_field")
def serializerTestTextFieldPK(self, format):
    data = [
        (
            pk_obj,
            1,
            TextPKData,
            """This is a long piece of text.
            It contains line breaks.
            Several of them.
            The end.""",
        ),
    ]
    assert_serializer(self, format, data)


register_tests(SerializerDataTests, "test_%s_serializer", serializerTest)
register_tests(SerializerDataTests, "test_%s_serializer_pk_0", serializerTestPK0)
register_tests(
    SerializerDataTests,
    "test_%s_serializer_null_value_string_field",
    serializerTestNullValueStingField,
)
register_tests(
    SerializerDataTests,
    "test_%s_serializer_text_field_pk",
    serializerTestTextFieldPK,
)
