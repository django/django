import warnings

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedAfterNextVersionWarning, RenameMethodsBase


class RenameManagerMethods(RenameMethodsBase):
    renamed_methods = (("old", "new", DeprecationWarning),)


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
        msg = "`Manager.old` method should be renamed `new`."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:

            class Manager(metaclass=RenameManagerMethods):
                def old(self):
                    pass

        self.assertEqual(ctx.filename, __file__)

    def test_get_new_defined(self):
        """
        Ensure `old` complains and not `new` when only `new` is defined.
        """

        class Manager(metaclass=RenameManagerMethods):
            def new(self):
                pass

        manager = Manager()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            manager.new()
        self.assertEqual(len(recorded), 0)

        msg = "`Manager.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            manager.old()
        self.assertEqual(ctx.filename, __file__)

    def test_get_old_defined(self):
        """
        Ensure `old` complains when only `old` is defined.
        """
        msg = "`Manager.old` method should be renamed `new`."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:

            class Manager(metaclass=RenameManagerMethods):
                def old(self):
                    pass

        self.assertEqual(ctx.filename, __file__)

        manager = Manager()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            manager.new()
        self.assertEqual(len(recorded), 0)

        msg = "`Manager.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            manager.old()
        self.assertEqual(ctx.filename, __file__)

    def test_deprecated_subclass_renamed(self):
        """
        Ensure the correct warnings are raised when a class that didn't rename
        `old` subclass one that did.
        """

        class Renamed(metaclass=RenameManagerMethods):
            def new(self):
                pass

        msg = "`Deprecated.old` method should be renamed `new`."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:

            class Deprecated(Renamed):
                def old(self):
                    super().old()

        self.assertEqual(ctx.filename, __file__)

        deprecated = Deprecated()

        msg = "`Renamed.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            deprecated.new()
        self.assertEqual(ctx.filename, __file__)

        msg = "`Deprecated.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            deprecated.old()
        self.assertEqual(ctx.filename, __file__)

    def test_renamed_subclass_deprecated(self):
        """
        Ensure the correct warnings are raised when a class that renamed
        `old` subclass one that didn't.
        """
        msg = "`Deprecated.old` method should be renamed `new`."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:

            class Deprecated(metaclass=RenameManagerMethods):
                def old(self):
                    pass

        self.assertEqual(ctx.filename, __file__)

        class Renamed(Deprecated):
            def new(self):
                super().new()

        renamed = Renamed()

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            renamed.new()
        self.assertEqual(len(recorded), 0)

        msg = "`Renamed.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            renamed.old()
        self.assertEqual(ctx.filename, __file__)

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

        msg = "`DeprecatedMixin.old` method should be renamed `new`."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:

            class Deprecated(DeprecatedMixin, RenamedMixin, Renamed):
                pass

        self.assertEqual(ctx.filename, __file__)

        deprecated = Deprecated()

        msg = "`RenamedMixin.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            deprecated.new()
        self.assertEqual(ctx.filename, __file__)

        msg = "`DeprecatedMixin.old` is deprecated, use `new` instead."
        with self.assertWarnsMessage(DeprecationWarning, msg) as ctx:
            deprecated.old()
        self.assertEqual(ctx.filename, __file__)

    def test_removedafternextversionwarning_pending(self):
        self.assertTrue(
            issubclass(RemovedAfterNextVersionWarning, PendingDeprecationWarning)
        )
