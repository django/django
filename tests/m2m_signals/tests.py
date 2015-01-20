"""
Testing signals emitted on changing m2m relations.
"""

from django.db import models
from django.test import TestCase

from .models import Part, Car, SportsCar, Person


class ManyToManySignalsTest(TestCase):
    def m2m_changed_signal_receiver(self, signal, sender, **kwargs):
        message = {
            'instance': kwargs['instance'],
            'action': kwargs['action'],
            'reverse': kwargs['reverse'],
            'model': kwargs['model'],
        }
        if kwargs['pk_set']:
            message['objects'] = list(
                kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
            )
        self.m2m_changed_messages.append(message)

    def setUp(self):
        self.m2m_changed_messages = []
        self.expected_messages = []

        self.c4 = SportsCar.objects.create(name='Bugatti', price='1000000')

        self.c4b = Car.objects.get(name='Bugatti')
        self.vw = Car.objects.create(name='VW')
        self.bmw = Car.objects.create(name='BMW')
        self.toyota = Car.objects.create(name='Toyota')
        self.wheelset = Part.objects.create(name='Wheelset')
        self.doors = Part.objects.create(name='Doors')
        self.engine = Part.objects.create(name='Engine')
        self.airbag = Part.objects.create(name='Airbag')
        self.sunroof = Part.objects.create(name='Sunroof')

        self.alice = Person.objects.create(name='Alice')
        self.bob = Person.objects.create(name='Bob')
        self.chuck = Person.objects.create(name='Chuck')
        self.daisy = Person.objects.create(name='Daisy')

        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Car.optional_parts.through
        )

        # Test the add, remove and clear methods on both sides of the
        # many-to-many relation

        # adding a default part to our car - no signal listener installed
        self.vw.default_parts.add(self.sunroof)

        # Now install a listener
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Car.default_parts.through
        )

        # Install liseners for self tests
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.fans.through
        )
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.friends.through
        )

    def tearDown(self):
        # disconnect all signal handlers
        models.signals.m2m_changed.disconnect(
            self.m2m_changed_signal_receiver, Car.default_parts.through
        )
        models.signals.m2m_changed.disconnect(
            self.m2m_changed_signal_receiver, Car.optional_parts.through
        )
        models.signals.m2m_changed.disconnect(
            self.m2m_changed_signal_receiver, Person.fans.through
        )
        models.signals.m2m_changed.disconnect(
            self.m2m_changed_signal_receiver, Person.friends.through
        )

    def test_m2m_relations_add_parts_signal(self):
        # Install a listener on one of the two m2m relations.
        self.vw.default_parts.add(self.wheelset, self.doors, self.engine)
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_reverse_add_parts_signal(self):
        # give the BMW and Toyata some doors as well
        self.doors.car_set.add(self.bmw, self.toyota)
        self.expected_messages.append({
            'instance': self.doors,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        self.expected_messages.append({
            'instance': self.doors,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_remove_parts_signal(self):
        # remove the engine from the self.vw and the airbag (which is not set
        # but is returned)
        self.vw.default_parts.remove(self.engine, self.airbag)
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.engine],
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.engine],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_add_optional_parts_signal(self):
        # give the self.vw some optional parts (second relation to same model)
        self.vw.optional_parts.add(self.airbag, self.sunroof)
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.sunroof],
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.sunroof],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_add_all_parts_signal(self):
        # add airbag to all the cars (even though the self.vw already has one)
        self.airbag.cars_optional.add(self.vw, self.bmw, self.toyota)
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota, self.vw],
        })
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota, self.vw],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_remove_optional_parts_reverse_signal(self):
        # remove airbag from the self.vw (reverse relation with custom
        # related_name)
        self.airbag.cars_optional.remove(self.vw)
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_remove',
            'reverse': True,
            'model': Car,
            'objects': [self.vw],
        })
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'post_remove',
            'reverse': True,
            'model': Car,
            'objects': [self.vw],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_clear_all_parts_signal(self):
        # clear all parts of the self.vw
        self.vw.default_parts.clear()
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_clear_part_signal(self):
        # take all the doors off of cars
        self.doors.car_set.clear()
        self.expected_messages.append({
            'instance': self.doors,
            'action': 'pre_clear',
            'reverse': True,
            'model': Car,
        })
        self.expected_messages.append({
            'instance': self.doors,
            'action': 'post_clear',
            'reverse': True,
            'model': Car,
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_clear_part_reverse_signal(self):
        # take all the airbags off of cars (clear reverse relation with custom
        # related_name)
        self.airbag.cars_optional.clear()
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_clear',
            'reverse': True,
            'model': Car,
        })
        self.expected_messages.append({
            'instance': self.airbag,
            'action': 'post_clear',
            'reverse': True,
            'model': Car,
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_add_part_alternative_signal(self):
        # alternative ways of setting relation:
        self.vw.default_parts.create(name='Windows')
        p6 = Part.objects.get(name='Windows')
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [p6],
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [p6],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_direct_assign_parts_signal(self):
        # direct assignment clears the set first, then adds
        self.vw.default_parts = [self.wheelset, self.doors, self.engine]
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_check_inheritance_signal(self):
        # Check that signals still work when model inheritance is involved
        self.c4.default_parts = [self.doors]
        self.expected_messages.append({
            'instance': self.c4,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        self.expected_messages.append({
            'instance': self.c4,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        self.expected_messages.append({
            'instance': self.c4,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors],
        })
        self.expected_messages.append({
            'instance': self.c4,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_check_inheritance_reverse_signal(self):
        self.engine.car_set.add(self.c4)
        self.expected_messages.append({
            'instance': self.engine,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [self.c4b],
        })
        self.expected_messages.append({
            'instance': self.engine,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [self.c4b],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_with_self(self):
        self.alice.friends = [self.bob, self.chuck]
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'pre_clear',
            'reverse': False,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'post_clear',
            'reverse': False,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'pre_add',
            'reverse': False,
            'model': Person,
            'objects': [self.bob, self.chuck],
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'post_add',
            'reverse': False,
            'model': Person,
            'objects': [self.bob, self.chuck],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_with_self1(self):
        self.alice.fans = [self.daisy]
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'pre_clear',
            'reverse': False,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'post_clear',
            'reverse': False,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'pre_add',
            'reverse': False,
            'model': Person,
            'objects': [self.daisy],
        })
        self.expected_messages.append({
            'instance': self.alice,
            'action': 'post_add',
            'reverse': False,
            'model': Person,
            'objects': [self.daisy],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)

    def test_m2m_relations_with_self2(self):
        self.chuck.idols = [self.alice, self.bob]
        self.expected_messages.append({
            'instance': self.chuck,
            'action': 'pre_clear',
            'reverse': True,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.chuck,
            'action': 'post_clear',
            'reverse': True,
            'model': Person,
        })
        self.expected_messages.append({
            'instance': self.chuck,
            'action': 'pre_add',
            'reverse': True,
            'model': Person,
            'objects': [self.alice, self.bob],
        })
        self.expected_messages.append({
            'instance': self.chuck,
            'action': 'post_add',
            'reverse': True,
            'model': Person,
            'objects': [self.alice, self.bob],
        })
        self.assertEqual(self.m2m_changed_messages, self.expected_messages)
