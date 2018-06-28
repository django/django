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
        msg = '`Manager.old` method should be renamed `new`.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            class Manager(metaclass=RenameManagerMethods):
                def old(self):
                    pass

    def test_get_new_defined(self):
        """
        Ensure `old` complains and not `new` when only `new` is defined.
        """
        class Manager(metaclass=RenameManagerMethods):
            def new(self):
                pass
        manager = Manager()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            manager.new()
        self.assertEqual(len(recorded), 0)

        msg = '`Manager.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            manager.old()

    def test_get_old_defined(self):
        """
        Ensure `old` complains when only `old` is defined.
        """
        class Manager(metaclass=RenameManagerMethods):
            def old(self):
                pass
        manager = Manager()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            manager.new()
        self.assertEqual(len(recorded), 0)

        msg = '`Manager.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            manager.old()

    def test_deprecated_subclass_renamed(self):
        """
        Ensure the correct warnings are raised when a class that didn't rename
        `old` subclass one that did.
        """
        class Renamed(metaclass=RenameManagerMethods):
            def new(self):
                pass

        class Deprecated(Renamed):
            def old(self):
                super().old()

        deprecated = Deprecated()

        msg = '`Renamed.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            deprecated.new()

        msg = '`Deprecated.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            deprecated.old()

    def test_renamed_subclass_deprecated(self):
        """
        Ensure the correct warnings are raised when a class that renamed
        `old` subclass one that didn't.
        """
        class Deprecated(metaclass=RenameManagerMethods):
            def old(self):
                pass

        class Renamed(Deprecated):
            def new(self):
                super().new()

        renamed = Renamed()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            renamed.new()
        self.assertEqual(len(recorded), 0)

        msg = '`Renamed.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            renamed.old()

    def test_deprecated_subclass_renamed_and_mixins(self):
        """
        Ensure the correct warnings are raised when a subclass inherit from a
        class that renamed `old` and mixins that may or may not have renamed
        `new`.
        """
        class Renamed(metaclass=RenameManagerMethods):
            def new(self):
                pass

        class RenamedMixin:
            def new(self):
                super().new()

        class DeprecatedMixin:
            def old(self):
                super().old()

        class Deprecated(DeprecatedMixin, RenamedMixin, Renamed):
            pass

        deprecated = Deprecated()

        msg = '`RenamedMixin.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            deprecated.new()

        msg = '`DeprecatedMixin.old` is deprecated, use `new` instead.'
        with self.assertWarnsMessage(DeprecationWarning, msg):
            deprecated.old()


class DeprecationInstanceCheckTest(SimpleTestCase):
    def test_warning(self):
        class Manager(metaclass=DeprecationInstanceCheck):
            alternative = 'fake.path.Foo'
            deprecation_warning = RemovedInNextVersionWarning

        msg = '`Manager` is deprecated, use `fake.path.Foo` instead.'
        with self.assertWarnsMessage(RemovedInNextVersionWarning, msg):
            isinstance(object, Manager)
