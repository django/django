from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.decorators import register
from django.contrib.admin.sites import site
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from .models import Location, Person, Place, Traveler


class NameAdmin(admin.ModelAdmin):
    list_display = ['name']
    save_on_top = True


class CustomSite(admin.AdminSite):
    pass


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
                         ['__str__'])
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

    def test_abstract_model(self):
        """
        Exception is raised when trying to register an abstract model.
        Refs #12004.
        """
        self.assertRaises(ImproperlyConfigured, self.site.register, Location)

    def test_is_registered_model(self):
        "Checks for registered models should return true."
        self.site.register(Person)
        self.assertTrue(self.site.is_registered(Person))

    def test_is_registered_not_registered_model(self):
        "Checks for unregistered models should return false."
        self.assertFalse(self.site.is_registered(Person))


class TestRegistrationDecorator(TestCase):
    """
    Tests the register decorator in admin.decorators

    For clarity:

        @register(Person)
        class AuthorAdmin(ModelAdmin):
            pass

    is functionally equal to (the way it is written in these tests):

        AuthorAdmin = register(Person)(AuthorAdmin)
    """
    def setUp(self):
        self.default_site = site
        self.custom_site = CustomSite()

    def test_basic_registration(self):
        register(Person)(NameAdmin)
        self.assertTrue(
            isinstance(self.default_site._registry[Person],
                       admin.options.ModelAdmin)
        )

    def test_custom_site_registration(self):
        register(Person, site=self.custom_site)(NameAdmin)
        self.assertTrue(
            isinstance(self.custom_site._registry[Person],
                       admin.options.ModelAdmin)
        )

    def test_multiple_registration(self):
        register(Traveler, Place)(NameAdmin)
        self.assertTrue(
            isinstance(self.default_site._registry[Traveler],
                       admin.options.ModelAdmin)
        )
        self.assertTrue(
            isinstance(self.default_site._registry[Place],
                       admin.options.ModelAdmin)
        )

    def test_wrapped_class_not_a_model_admin(self):
        self.assertRaisesMessage(ValueError, 'Wrapped class must subclass ModelAdmin.',
            register(Person), CustomSite)

    def test_custom_site_not_an_admin_site(self):
        self.assertRaisesMessage(ValueError, 'site must subclass AdminSite',
            register(Person, site=Traveler), NameAdmin)
