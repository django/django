import os
import shutil
from unittest import skipIf

from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.images import ImageFile
from django.db.models import signals
from django.test import TestCase
from django.test.testcases import SerializeMixin

try:
    from .models import Image
except ImproperlyConfigured:
    Image = None

if Image:
    from .models import (
        Person,
        PersonDimensionsFirst,
        PersonNoReadImage,
        PersonTwoImages,
        PersonWithHeight,
        PersonWithHeightAndWidth,
        TestImageFieldFile,
        temp_storage_dir,
    )
else:
    # Pillow not available, create dummy classes (tests will be skipped anyway)
    class Person:
        pass

    PersonWithHeight = PersonWithHeightAndWidth = PersonDimensionsFirst = Person
    PersonTwoImages = PersonNoReadImage = Person


class ImageFieldTestMixin(SerializeMixin):
    """
    Mixin class to provide common functionality to ImageField test classes.
    """

    lockfile = __file__

    # Person model to use for tests.
    PersonModel = PersonWithHeightAndWidth
    # File class to use for file instances.
    File = ImageFile

    def setUp(self):
        """
        Creates a pristine temp directory (or deletes and recreates if it
        already exists) that the model uses as its storage directory.

        Sets up two ImageFile instances for use in tests.
        """
        if os.path.exists(temp_storage_dir):
            shutil.rmtree(temp_storage_dir)
        os.mkdir(temp_storage_dir)
        self.addCleanup(shutil.rmtree, temp_storage_dir)
        file_path1 = os.path.join(os.path.dirname(__file__), "4x8.png")
        self.file1 = self.File(open(file_path1, "rb"), name="4x8.png")
        self.addCleanup(self.file1.close)
        file_path2 = os.path.join(os.path.dirname(__file__), "8x4.png")
        self.file2 = self.File(open(file_path2, "rb"), name="8x4.png")
        self.addCleanup(self.file2.close)

    def check_dimensions(self, instance, width, height, field_name="mugshot"):
        """
        Asserts that the given width and height values match both the
        field's height and width attributes and the height and width fields
        (if defined) the image field is caching to.

        Note, this method will check for dimension fields named by adding
        "_width" or "_height" to the name of the ImageField. So, the
        models used in these tests must have their fields named
        accordingly.

        By default, we check the field named "mugshot", but this can be
        specified by passing the field_name parameter.
        """
        field = getattr(instance, field_name)
        # Check height/width attributes of field.
        if width is None and height is None:
            with self.assertRaises(ValueError):
                getattr(field, "width")
            with self.assertRaises(ValueError):
                getattr(field, "height")
        else:
            self.assertEqual(field.width, width)
            self.assertEqual(field.height, height)

        # Check height/width fields of model, if defined.
        width_field_name = field_name + "_width"
        if hasattr(instance, width_field_name):
            self.assertEqual(getattr(instance, width_field_name), width)
        height_field_name = field_name + "_height"
        if hasattr(instance, height_field_name):
            self.assertEqual(getattr(instance, height_field_name), height)


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldTests(ImageFieldTestMixin, TestCase):
    """
    Tests for ImageField that don't need to be run with each of the
    different test model classes.
    """

    def test_equal_notequal_hash(self):
        """
        Bug #9786: Ensure '==' and '!=' work correctly.
        Bug #9508: make sure hash() works as expected (equal items must
        hash to the same value).
        """
        # Create two Persons with different mugshots.
        p1 = self.PersonModel(name="Joe")
        p1.mugshot.save("mug", self.file1)
        p2 = self.PersonModel(name="Bob")
        p2.mugshot.save("mug", self.file2)
        self.assertIs(p1.mugshot == p2.mugshot, False)
        self.assertIs(p1.mugshot != p2.mugshot, True)

        # Test again with an instance fetched from the db.
        p1_db = self.PersonModel.objects.get(name="Joe")
        self.assertIs(p1_db.mugshot == p2.mugshot, False)
        self.assertIs(p1_db.mugshot != p2.mugshot, True)

        # Instance from db should match the local instance.
        self.assertIs(p1_db.mugshot == p1.mugshot, True)
        self.assertEqual(hash(p1_db.mugshot), hash(p1.mugshot))
        self.assertIs(p1_db.mugshot != p1.mugshot, False)

    def test_instantiate_missing(self):
        """
        If the underlying file is unavailable, still create instantiate the
        object without error.
        """
        p = self.PersonModel(name="Joan")
        p.mugshot.save("shot", self.file1)
        p = self.PersonModel.objects.get(name="Joan")
        path = p.mugshot.path
        shutil.move(path, path + ".moved")
        self.PersonModel.objects.get(name="Joan")

    def test_delete_when_missing(self):
        """
        Bug #8175: correctly delete an object where the file no longer
        exists on the file system.
        """
        p = self.PersonModel(name="Fred")
        p.mugshot.save("shot", self.file1)
        os.remove(p.mugshot.path)
        p.delete()

    def test_size_method(self):
        """
        Bug #8534: FileField.size should not leave the file open.
        """
        p = self.PersonModel(name="Joan")
        p.mugshot.save("shot", self.file1)

        # Get a "clean" model instance
        p = self.PersonModel.objects.get(name="Joan")
        # It won't have an opened file.
        self.assertIs(p.mugshot.closed, True)

        # After asking for the size, the file should still be closed.
        p.mugshot.size
        self.assertIs(p.mugshot.closed, True)

    def test_pickle(self):
        """
        ImageField can be pickled, unpickled, and that the image of
        the unpickled version is the same as the original.
        """
        import pickle

        p = Person(name="Joe")
        p.mugshot.save("mug", self.file1)
        dump = pickle.dumps(p)

        loaded_p = pickle.loads(dump)
        self.assertEqual(p.mugshot, loaded_p.mugshot)
        self.assertEqual(p.mugshot.url, loaded_p.mugshot.url)
        self.assertEqual(p.mugshot.storage, loaded_p.mugshot.storage)
        self.assertEqual(p.mugshot.instance, loaded_p.mugshot.instance)
        self.assertEqual(p.mugshot.field, loaded_p.mugshot.field)

        mugshot_dump = pickle.dumps(p.mugshot)
        loaded_mugshot = pickle.loads(mugshot_dump)
        self.assertEqual(p.mugshot, loaded_mugshot)
        self.assertEqual(p.mugshot.url, loaded_mugshot.url)
        self.assertEqual(p.mugshot.storage, loaded_mugshot.storage)
        self.assertEqual(p.mugshot.instance, loaded_mugshot.instance)
        self.assertEqual(p.mugshot.field, loaded_mugshot.field)

    def test_defer(self):
        self.PersonModel.objects.create(name="Joe", mugshot=self.file1)
        with self.assertNumQueries(1):
            qs = list(self.PersonModel.objects.defer("mugshot"))
        with self.assertNumQueries(0):
            self.assertEqual(qs[0].name, "Joe")


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldTwoDimensionsTests(ImageFieldTestMixin, TestCase):
    """
    Tests behavior of an ImageField and its dimensions fields.
    """

    def test_constructor(self):
        """
        Tests assigning an image field through the model's constructor.
        """
        p = self.PersonModel(name="Joe", mugshot=self.file1)
        self.check_dimensions(p, 4, 8)
        p.save()
        self.check_dimensions(p, 4, 8)

    def test_image_after_constructor(self):
        """
        Tests behavior when image is not passed in constructor.
        """
        p = self.PersonModel(name="Joe")
        # TestImageField value will default to being an instance of its
        # attr_class, a  TestImageFieldFile, with name == None, which will
        # cause it to evaluate as False.
        self.assertIsInstance(p.mugshot, TestImageFieldFile)
        self.assertFalse(p.mugshot)

        # Test setting a fresh created model instance.
        p = self.PersonModel(name="Joe")
        p.mugshot = self.file1
        self.check_dimensions(p, 4, 8)

    def test_create(self):
        """
        Tests assigning an image in Manager.create().
        """
        p = self.PersonModel.objects.create(name="Joe", mugshot=self.file1)
        self.check_dimensions(p, 4, 8)

    def test_default_value(self):
        """
        The default value for an ImageField is an instance of
        the field's attr_class (TestImageFieldFile in this case) with no
        name (name set to None).
        """
        p = self.PersonModel()
        self.assertIsInstance(p.mugshot, TestImageFieldFile)
        self.assertFalse(p.mugshot)

    def test_assignment_to_None(self):
        """
        Assigning ImageField to None clears dimensions.
        """
        p = self.PersonModel(name="Joe", mugshot=self.file1)
        self.check_dimensions(p, 4, 8)

        # If image assigned to None, dimension fields should be cleared.
        p.mugshot = None
        self.check_dimensions(p, None, None)

        p.mugshot = self.file2
        self.check_dimensions(p, 8, 4)

    def test_field_save_and_delete_methods(self):
        """
        Tests assignment using the field's save method and deletion using
        the field's delete method.
        """
        p = self.PersonModel(name="Joe")
        p.mugshot.save("mug", self.file1)
        self.check_dimensions(p, 4, 8)

        # A new file should update dimensions.
        p.mugshot.save("mug", self.file2)
        self.check_dimensions(p, 8, 4)

        # Field and dimensions should be cleared after a delete.
        p.mugshot.delete(save=False)
        self.assertIsNone(p.mugshot.name)
        self.check_dimensions(p, None, None)

    def test_dimensions(self):
        """
        Dimensions are updated correctly in various situations.
        """
        p = self.PersonModel(name="Joe")

        # Dimensions should get set if file is saved.
        p.mugshot.save("mug", self.file1)
        self.check_dimensions(p, 4, 8)

        # Test dimensions after fetching from database.
        p = self.PersonModel.objects.get(name="Joe")
        # Bug 11084: Dimensions should not get recalculated if file is
        # coming from the database. We test this by checking if the file
        # was opened.
        self.assertIs(p.mugshot.was_opened, False)
        self.check_dimensions(p, 4, 8)
        # After checking dimensions on the image field, the file will have
        # opened.
        self.assertIs(p.mugshot.was_opened, True)
        # Dimensions should now be cached, and if we reset was_opened and
        # check dimensions again, the file should not have opened.
        p.mugshot.was_opened = False
        self.check_dimensions(p, 4, 8)
        self.assertIs(p.mugshot.was_opened, False)

        # If we assign a new image to the instance, the dimensions should
        # update.
        p.mugshot = self.file2
        self.check_dimensions(p, 8, 4)
        # Dimensions were recalculated, and hence file should have opened.
        self.assertIs(p.mugshot.was_opened, True)


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldNoDimensionsTests(ImageFieldTwoDimensionsTests):
    """
    Tests behavior of an ImageField with no dimension fields.
    """

    PersonModel = Person

    def test_post_init_not_connected(self):
        person_model_id = id(self.PersonModel)
        self.assertNotIn(
            person_model_id,
            [sender_id for (_, sender_id), *_ in signals.post_init.receivers],
        )

    def test_save_does_not_close_file(self):
        p = self.PersonModel(name="Joe")
        p.mugshot.save("mug", self.file1)
        with p.mugshot as f:
            # Underlying file object wasn’t closed.
            self.assertEqual(f.tell(), 0)


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldOneDimensionTests(ImageFieldTwoDimensionsTests):
    """
    Tests behavior of an ImageField with one dimensions field.
    """

    PersonModel = PersonWithHeight


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldDimensionsFirstTests(ImageFieldTwoDimensionsTests):
    """
    Tests behavior of an ImageField where the dimensions fields are
    defined before the ImageField.
    """

    PersonModel = PersonDimensionsFirst


@skipIf(Image is None, "Pillow is required to test ImageField")
class ImageFieldUsingFileTests(ImageFieldTwoDimensionsTests):
    """
    Tests behavior of an ImageField when assigning it a File instance
    rather than an ImageFile instance.
    """

    PersonModel = PersonDimensionsFirst
    File = File


@skipIf(Image is None, "Pillow is required to test ImageField")
class TwoImageFieldTests(ImageFieldTestMixin, TestCase):
    """
    Tests a model with two ImageFields.
    """

    PersonModel = PersonTwoImages

    def test_constructor(self):
        p = self.PersonModel(mugshot=self.file1, headshot=self.file2)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")
        p.save()
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")

    def test_create(self):
        p = self.PersonModel.objects.create(mugshot=self.file1, headshot=self.file2)
        self.check_dimensions(p, 4, 8)
        self.check_dimensions(p, 8, 4, "headshot")

    def test_assignment(self):
        p = self.PersonModel()
        self.check_dimensions(p, None, None, "mugshot")
        self.check_dimensions(p, None, None, "headshot")

        p.mugshot = self.file1
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, None, None, "headshot")
        p.headshot = self.file2
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")

        # Clear the ImageFields one at a time.
        p.mugshot = None
        self.check_dimensions(p, None, None, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")
        p.headshot = None
        self.check_dimensions(p, None, None, "mugshot")
        self.check_dimensions(p, None, None, "headshot")

    def test_field_save_and_delete_methods(self):
        p = self.PersonModel(name="Joe")
        p.mugshot.save("mug", self.file1)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, None, None, "headshot")
        p.headshot.save("head", self.file2)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")

        # We can use save=True when deleting the image field with null=True
        # dimension fields and the other field has an image.
        p.headshot.delete(save=True)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, None, None, "headshot")
        p.mugshot.delete(save=False)
        self.check_dimensions(p, None, None, "mugshot")
        self.check_dimensions(p, None, None, "headshot")

    def test_dimensions(self):
        """
        Dimensions are updated correctly in various situations.
        """
        p = self.PersonModel(name="Joe")

        # Dimensions should get set for the saved file.
        p.mugshot.save("mug", self.file1)
        p.headshot.save("head", self.file2)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")

        # Test dimensions after fetching from database.
        p = self.PersonModel.objects.get(name="Joe")
        # Bug 11084: Dimensions should not get recalculated if file is
        # coming from the database. We test this by checking if the file
        # was opened.
        self.assertIs(p.mugshot.was_opened, False)
        self.assertIs(p.headshot.was_opened, False)
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")
        # After checking dimensions on the image fields, the files will
        # have been opened.
        self.assertIs(p.mugshot.was_opened, True)
        self.assertIs(p.headshot.was_opened, True)
        # Dimensions should now be cached, and if we reset was_opened and
        # check dimensions again, the file should not have opened.
        p.mugshot.was_opened = False
        p.headshot.was_opened = False
        self.check_dimensions(p, 4, 8, "mugshot")
        self.check_dimensions(p, 8, 4, "headshot")
        self.assertIs(p.mugshot.was_opened, False)
        self.assertIs(p.headshot.was_opened, False)

        # If we assign a new image to the instance, the dimensions should
        # update.
        p.mugshot = self.file2
        p.headshot = self.file1
        self.check_dimensions(p, 8, 4, "mugshot")
        self.check_dimensions(p, 4, 8, "headshot")
        # Dimensions were recalculated, and hence file should have opened.
        self.assertIs(p.mugshot.was_opened, True)
        self.assertIs(p.headshot.was_opened, True)


@skipIf(Image is None, "Pillow is required to test ImageField")
class NoReadTests(ImageFieldTestMixin, TestCase):
    def test_width_height_correct_name_mangling_correct(self):
        instance1 = PersonNoReadImage()

        instance1.mugshot.save("mug", self.file1)

        self.assertEqual(instance1.mugshot_width, 4)
        self.assertEqual(instance1.mugshot_height, 8)

        instance1.save()

        self.assertEqual(instance1.mugshot_width, 4)
        self.assertEqual(instance1.mugshot_height, 8)

        instance2 = PersonNoReadImage()
        instance2.mugshot.save("mug", self.file1)
        instance2.save()

        self.assertNotEqual(instance1.mugshot.name, instance2.mugshot.name)

        self.assertEqual(instance1.mugshot_width, instance2.mugshot_width)
        self.assertEqual(instance1.mugshot_height, instance2.mugshot_height)
