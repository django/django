from django.db.models import CompositeField
from django.db.models.fields.composite import Subfield
from django.test import TestCase

from .models import ConstraintField


class TestUniqueConstraint(TestCase):
    def setUp(self):
        self.objs = [
            ConstraintField.objects.create(point={'x': 0, 'y': 0}),
            ConstraintField.objects.create(point={'x': 0, 'y': 1}),
            ConstraintField.objects.create(point={'x': 0, 'y': -1}),
            ConstraintField.objects.create(point={'x': 1, 'y': 0}),
            ConstraintField.objects.create(point={'x': 1, 'y': 1})
        ]
        self.meta = ConstraintField._meta
        self.field = self.meta.get_field('point')

    def test_composite_fields_subfields(self):
        self.assertIsInstance(
            self.field, CompositeField
        )
        self.assertEqual(
            self.field.subfields, {
                'x': Subfield(self.field, self.meta.get_field('x')),
                'y': Subfield(self.field, self.meta.get_field('y'))
            }
        )

    def test_subfield_params(self):
        x_subfield = self.field.subfields['x']
        self.assertEqual(x_subfield.attname, 'x')
        self.assertEqual(
            x_subfield.creation_counter,
            self.field.creation_counter
        )
        self.assertEqual(
            x_subfield.subfield_creation_counter,
            self.meta.get_field('x').creation_counter
        )

    def test_subfield_mutation(self):
        obj = self.objs[0]
        obj.point['x'] = 14
        self.assertEqual(obj.x, 14)

        obj.x = 15
        self.assertEqual(obj.point['x'], 15)

    def test_composite_transform_lookup(self):
        objs = ConstraintField.objects.filter(point__x=0).all()
        self.assertEquals(
            sorted(obj.pk for obj in objs),
            [self.objs[0].pk, self.objs[1].pk, self.objs[2].pk]
        )

        objs = ConstraintField.objects.filter(
            point__x=0, point__y__gte=0, point__y__lte=1
        ).all()
        self.assertEqual(
            sorted(obj.pk for obj in objs),
            [self.objs[0].pk, self.objs[1].pk]
        )

    def test_query_constraint(self):
        obj = ConstraintField.objects.get(point={'x': 0, 'y': 0})
        self.assertEquals(obj.pk, self.objs[0].pk)

    def test_values(self):
        objs = (
            ConstraintField.objects.filter(point__x=0)
            .values('point', 'y').all()
        )
        objs = list(objs)
        self.assertEqual(
            objs, [
                {'point': {'x': 0, 'y': 0}, 'y': 0},
                {'point': {'x': 0, 'y': 1}, 'y': 1},
                {'point': {'x': 0, 'y': -1}, 'y': -1}
            ]
        )
