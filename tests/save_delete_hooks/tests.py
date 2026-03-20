from django.test import TestCase

from .models import Person


class SaveDeleteHookTests(TestCase):
    def test_basic(self):
        p = Person(first_name="John", last_name="Smith")
        self.assertEqual(p.data, [])
        p.save()
        self.assertEqual(
            p.data,
            [
                "Before save",
                "After save",
            ],
        )

        self.assertQuerySetEqual(
            Person.objects.all(),
            [
                "John Smith",
            ],
            str,
        )

        p.delete()
        self.assertEqual(
            p.data,
            [
                "Before save",
                "After save",
                "Before deletion",
                "After deletion",
            ],
        )
        self.assertQuerySetEqual(Person.objects.all(), [])

    def test_hook_order_on_save(self):
        p = Person(first_name="Alice", last_name="Jones")
        p.save()
        self.assertEqual(p.data[0], "Before save")
        self.assertEqual(p.data[1], "After save")

    def test_hook_order_on_delete(self):
        p = Person.objects.create(first_name="Bob", last_name="Brown")
        p.data.clear()
        p.delete()
        self.assertEqual(p.data[0], "Before deletion")
        self.assertEqual(p.data[1], "After deletion")

    def test_hooks_fire_on_update(self):
        p = Person.objects.create(first_name="Carol", last_name="White")
        p.data.clear()
        p.first_name = "Caroline"
        p.save()
        self.assertEqual(
            p.data,
            ["Before save", "After save"],
        )
        p.refresh_from_db()
        self.assertEqual(p.first_name, "Caroline")

    def test_multiple_saves_accumulate_hooks(self):
        p = Person(first_name="Dan", last_name="Green")
        p.save()
        p.save()
        self.assertEqual(
            p.data,
            [
                "Before save",
                "After save",
                "Before save",
                "After save",
            ],
        )
