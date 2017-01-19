import warnings

from django.test import SimpleTestCase
from django.utils.deprecation import (
    DeprecationInstanceCheck, RemovedInNextVersionWarning, RenameMethodsBase,
)


class RenameManagerMethods(RenameMethodsBase):
    renamed_methods = (
        ('old', 'new', DeprecationWarning),
    )


class RenameMethodsTests(SimpleTestCase):
    """
    Tests the `RenameMethodsBase` type introduced to rename `get_query_set`
    to `get_queryset` across the code base following #15363.
    """

    def test_class_definition_warnings(self):
        """
        Ensure a warning is raised upon class definition to suggest renaming
        the faulty method.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')

            class Manager(metaclass=RenameManagerMethods):
                def old(self):
                    pass
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertEqual(msg, '`Manager.old` method should be renamed `new`.')

    def test_get_new_defined(self):
        """
        Ensure `old` complains and not `new` when only `new` is defined.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Manager(metaclass=RenameManagerMethods):
                def new(self):
                    pass
            warnings.simplefilter('always')
            manager = Manager()
            manager.new()
            self.assertEqual(len(recorded), 0)
            manager.old()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg, '`Manager.old` is deprecated, use `new` instead.')

    def test_get_old_defined(self):
        """
        Ensure `old` complains when only `old` is defined.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Manager(metaclass=RenameManagerMethods):
                def old(self):
                    pass
            warnings.simplefilter('always')
            manager = Manager()
            manager.new()
            self.assertEqual(len(recorded), 0)
            manager.old()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg, '`Manager.old` is deprecated, use `new` instead.')

    def test_deprecated_subclass_renamed(self):
        """
        Ensure the correct warnings are raised when a class that didn't rename
        `old` subclass one that did.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Renamed(metaclass=RenameManagerMethods):
                def new(self):
                    pass

            class Deprecated(Renamed):
                def old(self):
                    super(Deprecated, self).old()
            warnings.simplefilter('always')
            deprecated = Deprecated()
            deprecated.new()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg, '`Renamed.old` is deprecated, use `new` instead.')
            recorded[:] = []
            deprecated.old()
            self.assertEqual(len(recorded), 2)
            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                '`Deprecated.old` is deprecated, use `new` instead.',
                '`Renamed.old` is deprecated, use `new` instead.',
            ])

    def test_renamed_subclass_deprecated(self):
        """
        Ensure the correct warnings are raised when a class that renamed
        `old` subclass one that didn't.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Deprecated(metaclass=RenameManagerMethods):
                def old(self):
                    pass

            class Renamed(Deprecated):
                def new(self):
                    super(Renamed, self).new()
            warnings.simplefilter('always')
            renamed = Renamed()
            renamed.new()
            self.assertEqual(len(recorded), 0)
            renamed.old()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg, '`Renamed.old` is deprecated, use `new` instead.')

    def test_deprecated_subclass_renamed_and_mixins(self):
        """
        Ensure the correct warnings are raised when a subclass inherit from a
        class that renamed `old` and mixins that may or may not have renamed
        `new`.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Renamed(metaclass=RenameManagerMethods):
                def new(self):
                    pass

            class RenamedMixin:
                def new(self):
                    super(RenamedMixin, self).new()

            class DeprecatedMixin:
                def old(self):
                    super(DeprecatedMixin, self).old()

            class Deprecated(DeprecatedMixin, RenamedMixin, Renamed):
                pass
            warnings.simplefilter('always')
            deprecated = Deprecated()
            deprecated.new()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg, '`RenamedMixin.old` is deprecated, use `new` instead.')
            deprecated.old()
            self.assertEqual(len(recorded), 2)
            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                '`DeprecatedMixin.old` is deprecated, use `new` instead.',
                '`RenamedMixin.old` is deprecated, use `new` instead.',
            ])


class DeprecationInstanceCheckTest(SimpleTestCase):
    def test_warning(self):
        class Manager(metaclass=DeprecationInstanceCheck):
            alternative = 'fake.path.Foo'
            deprecation_warning = RemovedInNextVersionWarning

        msg = '`Manager` is deprecated, use `fake.path.Foo` instead.'
        with warnings.catch_warnings():
            warnings.simplefilter('error', category=RemovedInNextVersionWarning)
            with self.assertRaisesMessage(RemovedInNextVersionWarning, msg):
                isinstance(object, Manager)
