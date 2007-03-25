"""
A test spanning all the capabilities of all the serializers.

This class defines sample data and a dynamically generated
test case that is capable of testing the capabilities of 
the serializers. This includes all valid data values, plus
forward, backwards and self references.
"""


import unittest, datetime

from django.utils.functional import curry
from django.core import serializers
from django.db import transaction
from django.core import management

from models import *

# A set of functions that can be used to recreate
# test data objects of various kinds
def data_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data
    instance.save()    
    return instance

def generic_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data[0]
    instance.save()
    for tag in data[1:]:
        instance.tags.create(data=tag)
    return instance
    
def fk_create(pk, klass, data):
    instance = klass(id=pk)
    setattr(instance, 'data_id', data)
    instance.save()
    return instance
    
def m2m_create(pk, klass, data):
    instance = klass(id=pk)
    instance.save()
    instance.data = data
    return instance

def o2o_create(pk, klass, data):
    instance = klass()
    instance.data_id = data
    instance.save()
    return instance

def pk_create(pk, klass, data):
    instance = klass()
    instance.data = data
    instance.save()
    return instance

# A set of functions that can be used to compare
# test data objects of various kinds
def data_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, instance.data, 
                         "Objects with PK=%d not equal; expected '%s' (%s), got '%s' (%s)" % (pk,data, type(data), instance.data, type(instance.data)))

def generic_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data[0], instance.data)
    testcase.assertEqual(data[1:], [t.data for t in instance.tags.all()])
    
def fk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, instance.data_id)

def m2m_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, [obj.id for obj in instance.data.all()])

def o2o_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data_id)

def pk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data)
        
# Define some data types. Each data type is
# actually a pair of functions; one to create
# and one to compare objects of that type
data_obj = (data_create, data_compare)
generic_obj = (generic_create, generic_compare)
fk_obj = (fk_create, fk_compare)
m2m_obj = (m2m_create, m2m_compare)
o2o_obj = (o2o_create, o2o_compare)
pk_obj = (pk_create, pk_compare)

test_data = [
    # Format: (data type, PK value, Model Class, data)  
    (data_obj, 1, BooleanData, True),
    (data_obj, 2, BooleanData, False),
    (data_obj, 10, CharData, "Test Char Data"),
    (data_obj, 11, CharData, ""),
    (data_obj, 12, CharData, "None"),
    (data_obj, 13, CharData, "null"),
    (data_obj, 14, CharData, "NULL"),
    (data_obj, 15, CharData, None),
    (data_obj, 20, DateData, datetime.date(2006,6,16)),
    (data_obj, 21, DateData, None),
    (data_obj, 30, DateTimeData, datetime.datetime(2006,6,16,10,42,37)),
    (data_obj, 31, DateTimeData, None),
    (data_obj, 40, EmailData, "hovercraft@example.com"),
    (data_obj, 41, EmailData, None),
    (data_obj, 50, FileData, 'file:///foo/bar/whiz.txt'),
    (data_obj, 51, FileData, None),
    (data_obj, 60, FilePathData, "/foo/bar/whiz.txt"),
    (data_obj, 61, FilePathData, None),
    (data_obj, 70, FloatData, 12.345),
    (data_obj, 71, FloatData, -12.345),
    (data_obj, 72, FloatData, 0.0),
    (data_obj, 73, FloatData, None),
    (data_obj, 80, IntegerData, 123456789),
    (data_obj, 81, IntegerData, -123456789),
    (data_obj, 82, IntegerData, 0),
    (data_obj, 83, IntegerData, None),
    #(XX, ImageData
    (data_obj, 90, IPAddressData, "127.0.0.1"),
    (data_obj, 91, IPAddressData, None),
    (data_obj, 100, NullBooleanData, True),
    (data_obj, 101, NullBooleanData, False),
    (data_obj, 102, NullBooleanData, None),
    (data_obj, 110, PhoneData, "212-634-5789"),
    (data_obj, 111, PhoneData, None),
    (data_obj, 120, PositiveIntegerData, 123456789),
    (data_obj, 121, PositiveIntegerData, None),
    (data_obj, 130, PositiveSmallIntegerData, 12),
    (data_obj, 131, PositiveSmallIntegerData, None),
    (data_obj, 140, SlugData, "this-is-a-slug"),
    (data_obj, 141, SlugData, None),
    (data_obj, 150, SmallData, 12), 
    (data_obj, 151, SmallData, -12), 
    (data_obj, 152, SmallData, 0), 
    (data_obj, 153, SmallData, None), 
    (data_obj, 160, TextData, """This is a long piece of text.
It contains line breaks.
Several of them.
The end."""),
    (data_obj, 161, TextData, ""),
    (data_obj, 162, TextData, None),
    (data_obj, 170, TimeData, datetime.time(10,42,37)),
    (data_obj, 171, TimeData, None),
    (data_obj, 180, USStateData, "MA"),
    (data_obj, 181, USStateData, None),
    (data_obj, 190, XMLData, "<foo></foo>"),
    (data_obj, 191, XMLData, None),

    (generic_obj, 200, GenericData, ['Generic Object 1', 'tag1', 'tag2']),
    (generic_obj, 201, GenericData, ['Generic Object 2', 'tag2', 'tag3']),

    (data_obj, 300, Anchor, "Anchor 1"),
    (data_obj, 301, Anchor, "Anchor 2"),

    (fk_obj, 400, FKData, 300), # Post reference
    (fk_obj, 401, FKData, 500), # Pre reference
    (fk_obj, 402, FKData, None), # Empty reference

    (m2m_obj, 410, M2MData, []), # Empty set
    (m2m_obj, 411, M2MData, [300,301]), # Post reference
    (m2m_obj, 412, M2MData, [500,501]), # Pre reference
    (m2m_obj, 413, M2MData, [300,301,500,501]), # Pre and Post reference

    (o2o_obj, None, O2OData, 300), # Post reference
    (o2o_obj, None, O2OData, 500), # Pre reference

    (fk_obj, 430, FKSelfData, 431), # Pre reference
    (fk_obj, 431, FKSelfData, 430), # Post reference
    (fk_obj, 432, FKSelfData, None), # Empty reference

    (m2m_obj, 440, M2MSelfData, []),
    (m2m_obj, 441, M2MSelfData, []),
    (m2m_obj, 442, M2MSelfData, [440, 441]),
    (m2m_obj, 443, M2MSelfData, [445, 446]),
    (m2m_obj, 444, M2MSelfData, [440, 441, 445, 446]),
    (m2m_obj, 445, M2MSelfData, []),
    (m2m_obj, 446, M2MSelfData, []),

    (data_obj, 500, Anchor, "Anchor 3"),
    (data_obj, 501, Anchor, "Anchor 4"),

    (pk_obj, 601, BooleanPKData, True),
    (pk_obj, 602, BooleanPKData, False),
    (pk_obj, 610, CharPKData, "Test Char PKData"),
#     (pk_obj, 620, DatePKData, datetime.date(2006,6,16)),
#     (pk_obj, 630, DateTimePKData, datetime.datetime(2006,6,16,10,42,37)),
    (pk_obj, 640, EmailPKData, "hovercraft@example.com"),
    (pk_obj, 650, FilePKData, 'file:///foo/bar/whiz.txt'),
    (pk_obj, 660, FilePathPKData, "/foo/bar/whiz.txt"),
    (pk_obj, 670, FloatPKData, 12.345),
    (pk_obj, 671, FloatPKData, -12.345),
    (pk_obj, 672, FloatPKData, 0.0),
    (pk_obj, 680, IntegerPKData, 123456789),
    (pk_obj, 681, IntegerPKData, -123456789),
    (pk_obj, 682, IntegerPKData, 0),
#     (XX, ImagePKData
    (pk_obj, 690, IPAddressPKData, "127.0.0.1"),
    (pk_obj, 700, NullBooleanPKData, True),
    (pk_obj, 701, NullBooleanPKData, False),
    (pk_obj, 710, PhonePKData, "212-634-5789"),
    (pk_obj, 720, PositiveIntegerPKData, 123456789),
    (pk_obj, 730, PositiveSmallIntegerPKData, 12),
    (pk_obj, 740, SlugPKData, "this-is-a-slug"),
    (pk_obj, 750, SmallPKData, 12), 
    (pk_obj, 751, SmallPKData, -12), 
    (pk_obj, 752, SmallPKData, 0), 
#     (pk_obj, 760, TextPKData, """This is a long piece of text.
# It contains line breaks.
# Several of them.
# The end."""),
#    (pk_obj, 770, TimePKData, datetime.time(10,42,37)),
    (pk_obj, 780, USStatePKData, "MA"),
#     (pk_obj, 790, XMLPKData, "<foo></foo>"),
]
    
# Dynamically create serializer tests to ensure that all
# registered serializers are automatically tested.
class SerializerTests(unittest.TestCase):
    pass

def serializerTest(format, self):
    # Clear the database first
    management.flush(verbosity=0, interactive=False)    

    # Create all the objects defined in the test data
    objects = []
    transaction.enter_transaction_management()
    transaction.managed(True)
    for (func, pk, klass, datum) in test_data:
        objects.append(func[0](pk, klass, datum))
    transaction.commit()
    transaction.leave_transaction_management()

    # Add the generic tagged objects to the object list 
    objects.extend(Tag.objects.all())
    
    # Serialize the test database
    serialized_data = serializers.serialize(format, objects, indent=2)

    # Flush the database and recreate from the serialized data
    management.flush(verbosity=0, interactive=False)    
    transaction.enter_transaction_management()
    transaction.managed(True)
    for obj in serializers.deserialize(format, serialized_data):
        obj.save()
    transaction.commit()
    transaction.leave_transaction_management()

    # Assert that the deserialized data is the same 
    # as the original source
    for (func, pk, klass, datum) in test_data:
        func[1](self, pk, klass, datum)
    
for format in serializers.get_serializer_formats():
    setattr(SerializerTests, 'test_'+format+'_serializer', curry(serializerTest, format))
