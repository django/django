"""
Testing signals emitted on changing m2m relations.
"""

from .models import Person

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

    def test_m2m_relations_add_remove_clear(self):
        expected_messages = []

        # Install a listener on one of the two m2m relations.
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

        self.vw.default_parts.add(self.wheelset, self.doors, self.engine)
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # give the BMW and Toyata some doors as well
        self.doors.car_set.add(self.bmw, self.toyota)
        expected_messages.append({
            'instance': self.doors,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        expected_messages.append({
            'instance': self.doors,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # remove the engine from the self.vw and the airbag (which is not set
        # but is returned)
        self.vw.default_parts.remove(self.engine, self.airbag)
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.engine],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.engine],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # give the self.vw some optional parts (second relation to same model)
        self.vw.optional_parts.add(self.airbag, self.sunroof)
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.sunroof],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.airbag, self.sunroof],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # add airbag to all the cars (even though the self.vw already has one)
        self.airbag.cars_optional.add(self.vw, self.bmw, self.toyota)
        expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        expected_messages.append({
            'instance': self.airbag,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [self.bmw, self.toyota],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # remove airbag from the self.vw (reverse relation with custom
        # related_name)
        self.airbag.cars_optional.remove(self.vw)
        expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_remove',
            'reverse': True,
            'model': Car,
            'objects': [self.vw],
        })
        expected_messages.append({
            'instance': self.airbag,
            'action': 'post_remove',
            'reverse': True,
            'model': Car,
            'objects': [self.vw],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # clear all parts of the self.vw
        self.vw.default_parts.clear()
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # take all the doors off of cars
        self.doors.car_set.clear()
        expected_messages.append({
            'instance': self.doors,
            'action': 'pre_clear',
            'reverse': True,
            'model': Car,
        })
        expected_messages.append({
            'instance': self.doors,
            'action': 'post_clear',
            'reverse': True,
            'model': Car,
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # take all the airbags off of cars (clear reverse relation with custom
        # related_name)
        self.airbag.cars_optional.clear()
        expected_messages.append({
            'instance': self.airbag,
            'action': 'pre_clear',
            'reverse': True,
            'model': Car,
        })
        expected_messages.append({
            'instance': self.airbag,
            'action': 'post_clear',
            'reverse': True,
            'model': Car,
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # alternative ways of setting relation:
        self.vw.default_parts.create(name='Windows')
        p6 = Part.objects.get(name='Windows')
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [p6],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [p6],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # direct assignment clears the set first, then adds
        self.vw.default_parts = [self.wheelset,self.doors,self.engine]
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors, self.engine, self.wheelset],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        # Check that signals still work when model inheritance is involved
        c4 = SportsCar.objects.create(name='Bugatti', price='1000000')
        c4b = Car.objects.get(name='Bugatti')
        c4.default_parts = [self.doors]
        expected_messages.append({
            'instance': c4,
            'action': 'pre_clear',
            'reverse': False,
            'model': Part,
        })
        expected_messages.append({
            'instance': c4,
            'action': 'post_clear',
            'reverse': False,
            'model': Part,
        })
        expected_messages.append({
            'instance': c4,
            'action': 'pre_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors],
        })
        expected_messages.append({
            'instance': c4,
            'action': 'post_add',
            'reverse': False,
            'model': Part,
            'objects': [self.doors],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        self.engine.car_set.add(c4)
        expected_messages.append({
            'instance': self.engine,
            'action': 'pre_add',
            'reverse': True,
            'model': Car,
            'objects': [c4b],
        })
        expected_messages.append({
            'instance': self.engine,
            'action': 'post_add',
            'reverse': True,
            'model': Car,
            'objects': [c4b],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

    def test_m2m_relations_with_self(self):
        expected_messages = []

        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.fans.through
        )
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.friends.through
        )

        self.alice.friends = [self.bob, self.chuck]
        expected_messages.append({
            'instance': self.alice,
            'action': 'pre_clear',
            'reverse': False,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'post_clear',
            'reverse': False,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'pre_add',
            'reverse': False,
            'model': Person,
            'objects': [self.bob, self.chuck],
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'post_add',
            'reverse': False,
            'model': Person,
            'objects': [self.bob, self.chuck],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        self.alice.fans = [self.daisy]
        expected_messages.append({
            'instance': self.alice,
            'action': 'pre_clear',
            'reverse': False,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'post_clear',
            'reverse': False,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'pre_add',
            'reverse': False,
            'model': Person,
            'objects': [self.daisy],
        })
        expected_messages.append({
            'instance': self.alice,
            'action': 'post_add',
            'reverse': False,
            'model': Person,
            'objects': [self.daisy],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

        self.chuck.idols = [self.alice,self.bob]
        expected_messages.append({
            'instance': self.chuck,
            'action': 'pre_clear',
            'reverse': True,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.chuck,
            'action': 'post_clear',
            'reverse': True,
            'model': Person,
        })
        expected_messages.append({
            'instance': self.chuck,
            'action': 'pre_add',
            'reverse': True,
            'model': Person,
            'objects': [self.alice, self.bob],
        })
        expected_messages.append({
            'instance': self.chuck,
            'action': 'post_add',
            'reverse': True,
            'model': Person,
            'objects': [self.alice, self.bob],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)
