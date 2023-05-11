from django.test import TestCase

from .models import Bar, Baz, Foo


class DatabaseLevelCascadeTests(TestCase):
    # def test_foreign_key_on_delete_db_cascade(self):
    #     parent = Parent.objects.create(name="Akash")
    #     Child.objects.create(name="Akash", parent=parent)
    #     print(Child.objects.all())
    #     parent.delete()
    #     print(Child.objects.all())

    # def test_foreign_key_on_delete_db_do_nothing(self):
    #     parent = Parent.objects.create(name="Akash")
    #     Child.objects.create(name="Akash", parent=parent)
    #     print(Child.objects.all())
    #     parent.delete()
    #     print(Child.objects.all())

    def test_foreign_key_on_delete_db(self):
        foo = Foo.objects.create()
        bar = Bar.objects.create(foo=foo)
        Baz.objects.create(bar=bar)
        Baz.objects.create(bar=bar)
        Baz.objects.create(bar=bar)
        bar.delete()
