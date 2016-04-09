from __future__ import unicode_literals

import uuid

from django.forms import UUIDField, ValidationError
from django.test import SimpleTestCase


class UUIDFieldTest(SimpleTestCase):

    def test_uuidfield_1(self):
        field = UUIDField()
        value = field.clean('550e8400e29b41d4a716446655440000')
        self.assertEqual(value, uuid.UUID('550e8400e29b41d4a716446655440000'))

    def test_uuidfield_2(self):
        field = UUIDField(required=False)
        value = field.clean('')
        self.assertEqual(value, None)

    def test_uuidfield_3(self):
        field = UUIDField()
        with self.assertRaises(ValidationError) as cm:
            field.clean('550e8400')
        self.assertEqual(cm.exception.messages[0], 'Enter a valid UUID.')

    def test_uuidfield_4(self):
        field = UUIDField()
        value = field.prepare_value(uuid.UUID('550e8400e29b41d4a716446655440000'))
        self.assertEqual(value, '550e8400e29b41d4a716446655440000')
