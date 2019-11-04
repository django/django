"""
Testing signals emitted on changing m2m relations.
"""

from django.db import models
from django.test import TestCase

from .models import Car, Part, Person, SportsCar


class ManyToManySignalsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vw = Car.objects.create(name='VW')
        cls.bmw = Car.objects.create(name='BMW')
        cls.toyota = Car.objects.create(name='Toyota')

        cls.wheelset = Part.objects.create(name='Wheelset')
        cls.doors = Part.objects.create(name='Doors')
        cls.engine = Part.objects.create(name='Engine')
        cls.airbag = Part.objects.create(name='Airbag')
        cls.sunroof = Part.objects.create(name='Sunroof')

        cls.alice = Person.objects.create(name='Alice')
        cls.bob = Person.objects.create(name='Bob')
        cls.chuck = Person.objects.create(name='Chuck')
        cls.daisy = Person.objects.create(name='Daisy')

    def setUp(self):
        self.m2m_changed_messages = []

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

    def _initialize_signal_car(self, add_default_parts_before_set_signal=False):
        """ Install a listener on the two m2m relations. """
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Car.optional_parts.through
        )
        if add_default_parts_before_set_signal:
            # adding a default part to our car - no signal listener installed
            self.vw.default_parts.add(self.sunroof)
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Car.default_parts.through
        )

    def test_m2m_relations_add_remove_clear(self):
        expected_messages = []

        self._initialize_signal_car(add_default_parts_before_set_signal=True)

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

        # give the BMW and Toyota some doors as well
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

    def test_m2m_relations_signals_remove_relation(self):
        self._initialize_signal_car()
        # remove the engine from the self.vw and the airbag (which is not set
        # but is returned)
        self.vw.default_parts.remove(self.engine, self.airbag)
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.vw,
                'action': 'pre_remove',
                'reverse': False,
                'model': Part,
                'objects': [self.airbag, self.engine],
            }, {
                'instance': self.vw,
                'action': 'post_remove',
                'reverse': False,
                'model': Part,
                'objects': [self.airbag, self.engine],
            }
        ])

    def test_m2m_relations_signals_give_the_self_vw_some_optional_parts(self):
        expected_messages = []

        self._initialize_signal_car()

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

    def test_m2m_relations_signals_reverse_relation_with_custom_related_name(self):
        self._initialize_signal_car()
        # remove airbag from the self.vw (reverse relation with custom
        # related_name)
        self.airbag.cars_optional.remove(self.vw)
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.airbag,
                'action': 'pre_remove',
                'reverse': True,
                'model': Car,
                'objects': [self.vw],
            }, {
                'instance': self.airbag,
                'action': 'post_remove',
                'reverse': True,
                'model': Car,
                'objects': [self.vw],
            }
        ])

    def test_m2m_relations_signals_clear_all_parts_of_the_self_vw(self):
        self._initialize_signal_car()
        # clear all parts of the self.vw
        self.vw.default_parts.clear()
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.vw,
                'action': 'pre_clear',
                'reverse': False,
                'model': Part,
            }, {
                'instance': self.vw,
                'action': 'post_clear',
                'reverse': False,
                'model': Part,
            }
        ])

    def test_m2m_relations_signals_all_the_doors_off_of_cars(self):
        self._initialize_signal_car()
        # take all the doors off of cars
        self.doors.car_set.clear()
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.doors,
                'action': 'pre_clear',
                'reverse': True,
                'model': Car,
            }, {
                'instance': self.doors,
                'action': 'post_clear',
                'reverse': True,
                'model': Car,
            }
        ])

    def test_m2m_relations_signals_reverse_relation(self):
        self._initialize_signal_car()
        # take all the airbags off of cars (clear reverse relation with custom
        # related_name)
        self.airbag.cars_optional.clear()
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.airbag,
                'action': 'pre_clear',
                'reverse': True,
                'model': Car,
            }, {
                'instance': self.airbag,
                'action': 'post_clear',
                'reverse': True,
                'model': Car,
            }
        ])

    def test_m2m_relations_signals_alternative_ways(self):
        expected_messages = []

        self._initialize_signal_car()

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
        self.vw.default_parts.set([self.wheelset, self.doors, self.engine])
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_remove',
            'reverse': False,
            'model': Part,
            'objects': [p6],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_remove',
            'reverse': False,
            'model': Part,
            'objects': [p6],
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

    def test_m2m_relations_signals_clearing_removing(self):
        expected_messages = []

        self._initialize_signal_car(add_default_parts_before_set_signal=True)

        # set by clearing.
        self.vw.default_parts.set([self.wheelset, self.doors, self.engine], clear=True)
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

        # set by only removing what's necessary.
        self.vw.default_parts.set([self.wheelset, self.doors], clear=False)
        expected_messages.append({
            'instance': self.vw,
            'action': 'pre_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.engine],
        })
        expected_messages.append({
            'instance': self.vw,
            'action': 'post_remove',
            'reverse': False,
            'model': Part,
            'objects': [self.engine],
        })
        self.assertEqual(self.m2m_changed_messages, expected_messages)

    def test_m2m_relations_signals_when_inheritance(self):
        expected_messages = []

        self._initialize_signal_car(add_default_parts_before_set_signal=True)

        # Signals still work when model inheritance is involved
        c4 = SportsCar.objects.create(name='Bugatti', price='1000000')
        c4b = Car.objects.get(name='Bugatti')
        c4.default_parts.set([self.doors])
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

    def _initialize_signal_person(self):
        # Install a listener on the two m2m relations.
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.fans.through
        )
        models.signals.m2m_changed.connect(
            self.m2m_changed_signal_receiver, Person.friends.through
        )

    def test_m2m_relations_with_self_add_friends(self):
        self._initialize_signal_person()
        self.alice.friends.set([self.bob, self.chuck])
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.alice,
                'action': 'pre_add',
                'reverse': False,
                'model': Person,
                'objects': [self.bob, self.chuck],
            }, {
                'instance': self.alice,
                'action': 'post_add',
                'reverse': False,
                'model': Person,
                'objects': [self.bob, self.chuck],
            }
        ])

    def test_m2m_relations_with_self_add_fan(self):
        self._initialize_signal_person()
        self.alice.fans.set([self.daisy])
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.alice,
                'action': 'pre_add',
                'reverse': False,
                'model': Person,
                'objects': [self.daisy],
            }, {
                'instance': self.alice,
                'action': 'post_add',
                'reverse': False,
                'model': Person,
                'objects': [self.daisy],
            }
        ])

    def test_m2m_relations_with_self_add_idols(self):
        self._initialize_signal_person()
        self.chuck.idols.set([self.alice, self.bob])
        self.assertEqual(self.m2m_changed_messages, [
            {
                'instance': self.chuck,
                'action': 'pre_add',
                'reverse': True,
                'model': Person,
                'objects': [self.alice, self.bob],
            }, {
                'instance': self.chuck,
                'action': 'post_add',
                'reverse': True,
                'model': Person,
                'objects': [self.alice, self.bob],
            }
        ])
