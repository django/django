from django.test import TestCase
from django.utils.observables import ChangeRecord, Observable


class Observer(object):
    def __init__(self):
        self.changes = list()

    def handle_changes(self, change_records):
        self.changes.extend(change_records)


class MyObservableBase(Observable):
    def __init__(self):
        self._prop_base_value = '70 rpm'

    def _get_prop_base(self):
        return self._prop_base_value

    def _set_prop_base(self, value):
        self._prop_base_value = value

    inherited_property = property(_get_prop_base, _set_prop_base)
    shadowed_property = property(_get_prop_base, _set_prop_base)


class MyObservable(MyObservableBase):
    class_field = None

    def __init__(self):
        self.instance_field = None
        self._property_value = None
        super(MyObservable, self).__init__()

    def _get_prop(self):
        return self._property_value

    def _set_prop(self, value):
        self._property_value = value

    def _del_prop(self, value):
        del self._property_value

    instance_property = property(_get_prop, _set_prop)
    unsettable_property = property(_get_prop)
    deletable_property = property(_get_prop, _set_prop, _del_prop)
    shadowed_property = property(_get_prop, _set_prop)

    def __str__(self):
        return '<my_observable at {0}>'.format(id(self))


class ObservableMixinTest(TestCase):
    def setUp(self):
        self.observer = Observer()
        self._mkinstance()

    def _mkinstance(self):
        self.observer.changes.clear()
        self.instance = MyObservable()
        self.instance.add_observer(self.observer)

    def test_set_class_field(self):
        self.instance.class_field = 42
        # The class field value should change on the instance, but not on
        # the class
        self.assertEqual(self.instance.class_field, 42)
        self.assertIs(MyObservable.class_field, None)

        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, 'class_field',
                                   old=None, new=42)
        ])

        self.observer.changes.clear()
        # Changing the value on the class should not fire an event.
        MyObservable.class_field = 64
        # Just like python, setting the class field doesn't update any instance
        # which has a value for the field in it's __dict__
        self.assertEqual(self.instance.class_field, 42)
        self.assertEqual(self.observer.changes, [])

    def test_set_instance_field(self):
        self.instance.instance_field = 'hello'
        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, 'instance_field',
                                   old=None, new='hello')
        ])
        self.observer.changes.clear()

        self.instance.new_instance_field = 'world'
        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, 'new_instance_field',
                                   new='world')
        ])
        self.assertTrue(self.observer.changes[0].insert)

    def test_set_property(self):
        self.instance.instance_property = 'Rolling stones'
        # setting an instance property should actually call the descriptor
        # not just set it in the dict.
        self.assertEqual(self.instance.instance_property, 'Rolling stones')
        self.assertEqual(self.instance._property_value, 'Rolling stones')

        # It's easier if the changes to both attributes are recorded.
        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, '_property_value',
                         old=None, new='Rolling stones'),
            ChangeRecord.attribute(self.instance, 'instance_property',
                         old=None, new='Rolling stones')
        ])

        # Trying to set an unsettable property should raise an attribute error
        self.observer.changes.clear()
        with self.assertRaises(AttributeError):
            self.instance.unsettable_property = 'The beatles'
        self.assertEqual(self.observer.changes, [])

    def test_set_property_inherited(self):
        self.instance.inherited_property = '45 rpm'
        self.assertEqual(self.instance.inherited_property, '45 rpm')
        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, '_prop_base_value',
                                   old='70 rpm', new='45 rpm'),
            ChangeRecord.attribute(self.instance, 'inherited_property',
                                   old='70 rpm', new='45 rpm'),
        ])
        self.observer.changes.clear()

        self.instance.shadowed_property = '1600 rpm'
        self.assertEqual(self.observer.changes, [
            ChangeRecord.attribute(self.instance, '_property_value',
                                   old=None, new='1600 rpm'),
            ChangeRecord.attribute(self.instance, 'shadowed_property',
                                   old=None, new='1600 rpm')
        ])
