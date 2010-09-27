from django.test import TestCase

from django.contrib import admin

from models import Person, Place

class NameAdmin(admin.ModelAdmin):
    list_display = ['name']
    save_on_top = True

class TestRegistration(TestCase):
    def setUp(self):
        self.site = admin.AdminSite()

    def test_bare_registration(self):
        self.site.register(Person)
        self.assertTrue(
            isinstance(self.site._registry[Person], admin.options.ModelAdmin)
        )

    def test_registration_with_model_admin(self):
        self.site.register(Person, NameAdmin)
        self.assertTrue(
            isinstance(self.site._registry[Person], NameAdmin)
        )

    def test_prevent_double_registration(self):
        self.site.register(Person)
        self.assertRaises(admin.sites.AlreadyRegistered,
                          self.site.register,
                          Person)

    def test_registration_with_star_star_options(self):
        self.site.register(Person, search_fields=['name'])
        self.assertEqual(self.site._registry[Person].search_fields, ['name'])

    def test_star_star_overrides(self):
        self.site.register(Person, NameAdmin,
                           search_fields=["name"], list_display=['__str__'])
        self.assertEqual(self.site._registry[Person].search_fields, ['name'])
        self.assertEqual(self.site._registry[Person].list_display,
                         ['action_checkbox', '__str__'])
        self.assertTrue(self.site._registry[Person].save_on_top)

    def test_iterable_registration(self):
        self.site.register([Person, Place], search_fields=['name'])
        self.assertTrue(
            isinstance(self.site._registry[Person], admin.options.ModelAdmin)
        )
        self.assertEqual(self.site._registry[Person].search_fields, ['name'])
        self.assertTrue(
            isinstance(self.site._registry[Place], admin.options.ModelAdmin)
        )
        self.assertEqual(self.site._registry[Place].search_fields, ['name'])
