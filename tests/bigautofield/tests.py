from __future__ import unicode_literals

from django.db import connection
from django.test import TestCase

from .models import Village, Population, City, Weather


class BigAutoFieldTest(TestCase):

    def test_type(self):
        field = Village._meta.get_field_by_name('id')[0]
        self.assertEqual(field.get_internal_type(), 'AutoField')
        types = {
            'mysql': 'integer AUTO_INCREMENT', 'oracle': 'NUMBER(11)',
            'postgresql': 'serial', 'sqlite': 'integer',
        }
        self.assertEqual(field.db_type(connection), types[connection.vendor])

        field = Population._meta.get_field_by_name('village')[0]
        types = {
            'mysql': 'integer', 'oracle': 'NUMBER(11)',
            'postgresql': 'integer', 'sqlite': 'integer',
        }
        self.assertEqual(field.db_type(connection), types[connection.vendor])

    def test_big_type(self):

        field = City._meta.get_field_by_name('id')[0]
        self.assertEqual(field.get_internal_type(), 'BigAutoField')
        types = {
            'mysql': 'bigint AUTO_INCREMENT', 'oracle': 'NUMBER(19)',
            'postgresql': 'bigserial', 'sqlite': 'integer',
        }
        self.assertEqual(field.db_type(connection), types[connection.vendor])

        field = Weather._meta.get_field_by_name('city')[0]
        types = {
            'mysql': 'bigint', 'oracle': 'NUMBER(19)',
            'postgresql': 'bigint', 'sqlite': 'bigint',
        }
        self.assertEqual(field.db_type(connection), types[connection.vendor])

    def test_usage(self):
        city_id = 8223372036854775807
        c = City.objects.create(id=city_id, name='Moscow')
        Weather.objects.create(city=c, temp=17)

        c = City.objects.get(id=city_id)
        w = Weather.objects.get(city_id=city_id)
        self.assertEqual(c.id, city_id)
        self.assertEqual(w.city_id, city_id)

        c.delete()

        with self.assertRaises(Weather.DoesNotExist):
            Weather.objects.get(city_id=city_id)
