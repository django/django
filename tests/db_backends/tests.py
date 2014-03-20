from django.test import TestCase
from django.db.backends import BaseDatabaseWrapper


class DummyDatabaseWrapper(BaseDatabaseWrapper):
    pass


class DummyObject(object):
    alias = None


class DbBackendTests(TestCase):
    def test_compare_db_wrapper_with_another_object(self):
        wrapper = BaseDatabaseWrapper({})
        self.assertFalse(wrapper == 'not-a-db-wrapper')

    def test_compare_db_wrapper_with_another_object_with_alias(self):
        wrapper = BaseDatabaseWrapper({})
        obj = DummyObject()
        obj.alias = wrapper.alias = 'foobar'
        self.assertFalse(wrapper == obj)

    def test_negate_compare_db_wrapper_with_another_object(self):
        wrapper = BaseDatabaseWrapper({})
        self.assertTrue(wrapper != 'not-a-db-wrapper')

    def test_compare_db_wrappers(self):
        wrapper1 = DummyDatabaseWrapper({})
        wrapper2 = BaseDatabaseWrapper({})

        wrapper1.alias = wrapper2.alias = 'foo'
        self.assertTrue(wrapper1 == wrapper2)

        wrapper1.alias = 'bar'
        self.assertFalse(wrapper1 == wrapper2)
