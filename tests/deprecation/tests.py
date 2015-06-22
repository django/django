from __future__ import unicode_literals

import os
import unittest
import warnings

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import reset_warning_registry
from django.utils import six, translation
from django.utils.deprecation import RenameMethodsBase
from django.utils.encoding import force_text
from django.utils.functional import memoize


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
        reset_warning_registry()
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')

            class Manager(six.with_metaclass(RenameManagerMethods)):
                def old(self):
                    pass
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertEqual(msg,
                '`Manager.old` method should be renamed `new`.')

    def test_get_new_defined(self):
        """
        Ensure `old` complains and not `new` when only `new` is defined.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Manager(six.with_metaclass(RenameManagerMethods)):
                def new(self):
                    pass
            warnings.simplefilter('always')
            manager = Manager()
            manager.new()
            self.assertEqual(len(recorded), 0)
            manager.old()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg,
                '`Manager.old` is deprecated, use `new` instead.')

    def test_get_old_defined(self):
        """
        Ensure `old` complains when only `old` is defined.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Manager(six.with_metaclass(RenameManagerMethods)):
                def old(self):
                    pass
            warnings.simplefilter('always')
            manager = Manager()
            manager.new()
            self.assertEqual(len(recorded), 0)
            manager.old()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg,
                '`Manager.old` is deprecated, use `new` instead.')

    def test_deprecated_subclass_renamed(self):
        """
        Ensure the correct warnings are raised when a class that didn't rename
        `old` subclass one that did.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Renamed(six.with_metaclass(RenameManagerMethods)):
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
            self.assertEqual(msg,
                '`Renamed.old` is deprecated, use `new` instead.')
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

            class Deprecated(six.with_metaclass(RenameManagerMethods)):
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
            self.assertEqual(msg,
                '`Renamed.old` is deprecated, use `new` instead.')

    def test_deprecated_subclass_renamed_and_mixins(self):
        """
        Ensure the correct warnings are raised when a subclass inherit from a
        class that renamed `old` and mixins that may or may not have renamed
        `new`.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('ignore')

            class Renamed(six.with_metaclass(RenameManagerMethods)):
                def new(self):
                    pass

            class RenamedMixin(object):
                def new(self):
                    super(RenamedMixin, self).new()

            class DeprecatedMixin(object):
                def old(self):
                    super(DeprecatedMixin, self).old()

            class Deprecated(DeprecatedMixin, RenamedMixin, Renamed):
                pass
            warnings.simplefilter('always')
            deprecated = Deprecated()
            deprecated.new()
            self.assertEqual(len(recorded), 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg,
                '`RenamedMixin.old` is deprecated, use `new` instead.')
            deprecated.old()
            self.assertEqual(len(recorded), 2)
            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                '`DeprecatedMixin.old` is deprecated, use `new` instead.',
                '`RenamedMixin.old` is deprecated, use `new` instead.',
            ])


class DeprecatingRequestMergeDictTest(SimpleTestCase):
    def test_deprecated_request(self):
        """
        Ensure the correct warning is raised when WSGIRequest.REQUEST is
        accessed.
        """
        reset_warning_registry()
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            request = RequestFactory().get('/')
            request.REQUEST  # evaluate

            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                '`request.REQUEST` is deprecated, use `request.GET` or '
                '`request.POST` instead.',
                '`MergeDict` is deprecated, use `dict.update()` instead.',
            ])


@override_settings(USE_I18N=True)
class DeprecatedChineseLanguageCodes(SimpleTestCase):
    def test_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            with translation.override('zh-cn'):
                pass
            with translation.override('zh-tw'):
                pass
            msgs = [str(warning.message) for warning in recorded]
            self.assertEqual(msgs, [
                "The use of the language code 'zh-cn' is deprecated. "
                "Please use the 'zh-hans' translation instead.",
                "The use of the language code 'zh-tw' is deprecated. "
                "Please use the 'zh-hant' translation instead.",
            ])


class DeprecatingMemoizeTest(SimpleTestCase):
    def test_deprecated_memoize(self):
        """
        Ensure the correct warning is raised when memoize is used.
        """
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            memoize(lambda x: x, {}, 1)
            msg = str(recorded.pop().message)
            self.assertEqual(msg,
                'memoize wrapper is deprecated and will be removed in Django '
                '1.9. Use django.utils.lru_cache instead.')


class DeprecatingSimpleTestCaseUrls(unittest.TestCase):

    def test_deprecation(self):
        """
        Ensure the correct warning is raised when SimpleTestCase.urls is used.
        """
        class TempTestCase(SimpleTestCase):
            urls = 'tests.urls'

            def test(self):
                pass

        with warnings.catch_warnings(record=True) as recorded:
            warnings.filterwarnings('always')
            suite = unittest.TestLoader().loadTestsFromTestCase(TempTestCase)
            with open(os.devnull, 'w') as devnull:
                unittest.TextTestRunner(stream=devnull, verbosity=2).run(suite)
                msg = force_text(recorded.pop().message)
                self.assertEqual(msg,
                    "SimpleTestCase.urls is deprecated and will be removed in "
                    "Django 1.10. Use @override_settings(ROOT_URLCONF=...) "
                    "in TempTestCase instead.")
