# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.utils import six
from django.utils.metaclassmaker import six_with_metaclassmaker


class MetaClassTest(unittest.TestCase):

    def test_six_with_metaclassmaker(self):
        class Dummy1MetaClass(type):
            def __init__(cls, name, bases, nmspc):
                super(Dummy1MetaClass, cls).__init__(name, bases, nmspc)
                if not hasattr(cls, 'meta_attr'):
                    setattr(cls, 'meta_attr', True)

        class Dummy2MetaClass(type):
            def __init__(cls, name, bases, nmspc):
                super(Dummy2MetaClass, cls).__init__(name, bases, nmspc)
                if not hasattr(cls, 'meta_attr2'):
                    setattr(cls, 'meta_attr2', True)

        class NormalClass(six.with_metaclass(Dummy1MetaClass, object)):
            normal_attr = True

        class MixinClass(six.with_metaclass(Dummy2MetaClass, object)):
            mixin_attr = True

        class MetaclassTestModel(six_with_metaclassmaker(NormalClass, MixinClass)):
            pass

        obj = MetaclassTestModel()
        self.assertIsInstance(obj, MixinClass)
        self.assertIsInstance(obj, NormalClass)
        self.assertEqual(getattr(obj, 'mixin_attr', False), True)
        self.assertEqual(getattr(obj, 'normal_attr', False), True)
        self.assertEqual(getattr(obj, 'meta_attr', False), True)
        self.assertEqual(getattr(obj, 'meta_attr2', False), True)
