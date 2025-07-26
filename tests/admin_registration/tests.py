from django.contrib import admin
from django.contrib.admin.decorators import register
from django.contrib.admin.exceptions import AlreadyRegistered, NotRegistered
from django.contrib.admin.sites import site
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from .models import Guest, Location, Person, Place, Traveler


class NameAdmin(admin.ModelAdmin):
    list_display = ["name"]
    save_on_top = True


class CustomSite(admin.AdminSite):
    pass


class TestRegistration(SimpleTestCase):
    def setUp(self):
        self.site = admin.AdminSite()

    def test_bare_registration(self):
        self.site.register(Person)
        self.assertIsInstance(self.site.get_model_admin(Person), admin.ModelAdmin)
        self.site.unregister(Person)
        self.assertEqual(self.site._registry, {})

    def test_registration_with_model_admin(self):
        self.site.register(Person, NameAdmin)
        self.assertIsInstance(self.site.get_model_admin(Person), NameAdmin)
        self.site.unregister(Person)
        self.assertEqual(self.site._registry, {})

    def test_prevent_double_registration(self):
        self.site.register(Person)
        msg = "The model Person is already registered in app 'admin_registration'."
        with self.assertRaisesMessage(AlreadyRegistered, msg):
            self.site.register(Person)

    def test_prevent_double_registration_for_custom_admin(self):
        class PersonAdmin(admin.ModelAdmin):
            pass

        self.site.register(Person, PersonAdmin)
        msg = (
            "The model Person is already registered with "
            "'admin_registration.PersonAdmin'."
        )
        with self.assertRaisesMessage(AlreadyRegistered, msg):
            self.site.register(Person, PersonAdmin)

    def test_unregister_unregistered_model(self):
        msg = "The model Person is not registered"
        with self.assertRaisesMessage(NotRegistered, msg):
            self.site.unregister(Person)

    def test_registration_with_star_star_options(self):
        self.site.register(Person, search_fields=["name"])
        self.assertEqual(self.site.get_model_admin(Person).search_fields, ["name"])

    def test_get_model_admin_unregister_model(self):
        msg = "The model Person is not registered."
        with self.assertRaisesMessage(NotRegistered, msg):
            self.site.get_model_admin(Person)

    def test_star_star_overrides(self):
        self.site.register(
            Person, NameAdmin, search_fields=["name"], list_display=["__str__"]
        )
        person_admin = self.site.get_model_admin(Person)
        self.assertEqual(person_admin.search_fields, ["name"])
        self.assertEqual(person_admin.list_display, ["__str__"])
        self.assertIs(person_admin.save_on_top, True)

    def test_iterable_registration(self):
        self.site.register([Person, Place], search_fields=["name"])
        self.assertIsInstance(self.site.get_model_admin(Person), admin.ModelAdmin)
        self.assertEqual(self.site.get_model_admin(Person).search_fields, ["name"])
        self.assertIsInstance(self.site.get_model_admin(Place), admin.ModelAdmin)
        self.assertEqual(self.site.get_model_admin(Place).search_fields, ["name"])
        self.site.unregister([Person, Place])
        self.assertEqual(self.site._registry, {})

    def test_abstract_model(self):
        """
        Exception is raised when trying to register an abstract model.
        Refs #12004.
        """
        msg = "The model Location is abstract, so it cannot be registered with admin."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.site.register(Location)

    def test_composite_pk_model(self):
        msg = (
            "The model Guest has a composite primary key, so it cannot be registered "
            "with admin."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.site.register(Guest)

    def test_is_registered_model(self):
        "Checks for registered models should return true."
        self.site.register(Person)
        self.assertTrue(self.site.is_registered(Person))

    def test_is_registered_not_registered_model(self):
        "Checks for unregistered models should return false."
        self.assertFalse(self.site.is_registered(Person))


class TestRegistrationDecorator(SimpleTestCase):
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
        self.assertIsInstance(
            self.default_site.get_model_admin(Person), admin.ModelAdmin
        )
        self.default_site.unregister(Person)

    def test_custom_site_registration(self):
        register(Person, site=self.custom_site)(NameAdmin)
        self.assertIsInstance(
            self.custom_site.get_model_admin(Person), admin.ModelAdmin
        )

    def test_multiple_registration(self):
        register(Traveler, Place)(NameAdmin)
        self.assertIsInstance(
            self.default_site.get_model_admin(Traveler), admin.ModelAdmin
        )
        self.default_site.unregister(Traveler)
        self.assertIsInstance(
            self.default_site.get_model_admin(Place), admin.ModelAdmin
        )
        self.default_site.unregister(Place)

    def test_wrapped_class_not_a_model_admin(self):
        with self.assertRaisesMessage(
            ValueError, "Wrapped class must subclass ModelAdmin."
        ):
            register(Person)(CustomSite)

    def test_custom_site_not_an_admin_site(self):
        with self.assertRaisesMessage(ValueError, "site must subclass AdminSite"):
            register(Person, site=Traveler)(NameAdmin)

    def test_empty_models_list_registration_fails(self):
        with self.assertRaisesMessage(
            ValueError, "At least one model must be passed to register."
        ):
            register()(NameAdmin)
