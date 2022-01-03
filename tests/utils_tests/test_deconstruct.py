from django.test import SimpleTestCase
from django.utils.deconstruct import deconstructible
from django.utils.version import get_docs_version


@deconstructible()
class DeconstructibleClass:
    pass


class DeconstructibleChildClass(DeconstructibleClass):
    pass


@deconstructible(
    path='utils_tests.deconstructible_classes.DeconstructibleWithPathClass'
)
class DeconstructibleWithPathClass:
    pass


@deconstructible(
    path='utils_tests.deconstructible_classes.DeconstructibleInvalidPathClass',
)
class DeconstructibleInvalidPathClass:
    pass


class DeconstructibleTests(SimpleTestCase):
    def test_deconstruct(self):
        obj = DeconstructibleClass('arg', key='value')
        path, args, kwargs = obj.deconstruct()
        self.assertEqual(path, 'utils_tests.test_deconstruct.DeconstructibleClass')
        self.assertEqual(args, ('arg',))
        self.assertEqual(kwargs, {'key': 'value'})

    def test_deconstruct_with_path(self):
        obj = DeconstructibleWithPathClass('arg', key='value')
        path, args, kwargs = obj.deconstruct()
        self.assertEqual(
            path,
            'utils_tests.deconstructible_classes.DeconstructibleWithPathClass',
        )
        self.assertEqual(args, ('arg',))
        self.assertEqual(kwargs, {'key': 'value'})

    def test_deconstruct_child(self):
        obj = DeconstructibleChildClass('arg', key='value')
        path, args, kwargs = obj.deconstruct()
        self.assertEqual(path, 'utils_tests.test_deconstruct.DeconstructibleChildClass')
        self.assertEqual(args, ('arg',))
        self.assertEqual(kwargs, {'key': 'value'})

    def test_invalid_path(self):
        obj = DeconstructibleInvalidPathClass()
        docs_version = get_docs_version()
        msg = (
            f'Could not find object DeconstructibleInvalidPathClass in '
            f'utils_tests.deconstructible_classes.\n'
            f'Please note that you cannot serialize things like inner '
            f'classes. Please move the object into the main module body to '
            f'use migrations.\n'
            f'For more information, see '
            f'https://docs.djangoproject.com/en/{docs_version}/topics/'
            f'migrations/#serializing-values'
        )
        with self.assertRaisesMessage(ValueError, msg):
            obj.deconstruct()
