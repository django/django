from django.test import TestCase

from .models import ChoicesModel, TestIntegerChoices, TestTextChoices


class TextChoicesFieldTests(TestCase):
    def test_created_instance_has_correct_type(self):
        """
        Test that when a model instance is created with a TextChoices value,
        the field value is immediately converted to a plain string.
        """
        obj = ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )

        # The value should be a string, not an enum
        self.assertIsInstance(obj.text_choice, str)
        self.assertNotIsInstance(obj.text_choice, TestTextChoices)
        self.assertEqual(obj.text_choice, "first")
        self.assertEqual(str(obj.text_choice), "first")

    def test_retrieved_instance_has_correct_type(self):
        """
        Test that when a model instance is retrieved from the database,
        the field value is a plain string.
        """
        ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )
        obj = ChoicesModel.objects.last()

        # The value should be a string, not an enum
        self.assertIsInstance(obj.text_choice, str)
        self.assertNotIsInstance(obj.text_choice, TestTextChoices)
        self.assertEqual(obj.text_choice, "first")
        self.assertEqual(str(obj.text_choice), "first")

    def test_consistency_between_created_and_retrieved(self):
        """
        Test that the field value has the same type and string representation
        for both created and retrieved instances.
        """
        created_obj = ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )
        retrieved_obj = ChoicesModel.objects.last()

        # Both should have the same type and value
        self.assertEqual(type(created_obj.text_choice), type(retrieved_obj.text_choice))
        self.assertEqual(str(created_obj.text_choice), str(retrieved_obj.text_choice))
        self.assertEqual(created_obj.text_choice, retrieved_obj.text_choice)


class IntegerChoicesFieldTests(TestCase):
    def test_created_instance_has_correct_type(self):
        """
        Test that when a model instance is created with an IntegerChoices value,
        the field value is immediately converted to a plain int.
        """
        obj = ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )

        # The value should be an int, not an enum
        self.assertIsInstance(obj.int_choice, int)
        self.assertNotIsInstance(obj.int_choice, TestIntegerChoices)
        self.assertEqual(obj.int_choice, 1)
        self.assertEqual(str(obj.int_choice), "1")

    def test_retrieved_instance_has_correct_type(self):
        """
        Test that when a model instance is retrieved from the database,
        the field value is a plain int.
        """
        ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )
        obj = ChoicesModel.objects.last()

        # The value should be an int, not an enum
        self.assertIsInstance(obj.int_choice, int)
        self.assertNotIsInstance(obj.int_choice, TestIntegerChoices)
        self.assertEqual(obj.int_choice, 1)
        self.assertEqual(str(obj.int_choice), "1")

    def test_consistency_between_created_and_retrieved(self):
        """
        Test that the field value has the same type and string representation
        for both created and retrieved instances.
        """
        created_obj = ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )
        retrieved_obj = ChoicesModel.objects.last()

        # Both should have the same type and value
        self.assertEqual(type(created_obj.int_choice), type(retrieved_obj.int_choice))
        self.assertEqual(str(created_obj.int_choice), str(retrieved_obj.int_choice))
        self.assertEqual(created_obj.int_choice, retrieved_obj.int_choice)

    def test_assignment_after_creation(self):
        """
        Test that assigning an enum value after creation also converts it properly.
        """
        obj = ChoicesModel.objects.create(
            text_choice=TestTextChoices.FIRST,
            int_choice=TestIntegerChoices.ONE
        )

        # Assign a new enum value
        obj.text_choice = TestTextChoices.SECOND
        obj.int_choice = TestIntegerChoices.TWO

        # The values should be converted to primitives
        self.assertIsInstance(obj.text_choice, str)
        self.assertEqual(obj.text_choice, "second")
        self.assertIsInstance(obj.int_choice, int)
        self.assertEqual(obj.int_choice, 2)

    def test_plain_value_assignment(self):
        """
        Test that assigning plain values still works correctly.
        """
        obj = ChoicesModel.objects.create(
            text_choice="first",
            int_choice=1
        )

        # The values should remain as primitives
        self.assertIsInstance(obj.text_choice, str)
        self.assertEqual(obj.text_choice, "first")
        self.assertIsInstance(obj.int_choice, int)
        self.assertEqual(obj.int_choice, 1)
