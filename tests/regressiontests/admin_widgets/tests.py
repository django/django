from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from unittest import TestCase
from django.test import TestCase as DjangoTestCase
import models

class AdminFormfieldForDBFieldTests(TestCase):
    """
    Tests for correct behavior of ModelAdmin.formfield_for_dbfield
    """

    def assertFormfield(self, model, fieldname, widgetclass, **admin_overrides):
        """
        Helper to call formfield_for_dbfield for a given model and field name
        and verify that the returned formfield is appropriate.
        """
        # Override any settings on the model admin
        class MyModelAdmin(admin.ModelAdmin): pass
        for k in admin_overrides:
            setattr(MyModelAdmin, k, admin_overrides[k])

        # Construct the admin, and ask it for a formfield
        ma = MyModelAdmin(model, admin.site)
        ff = ma.formfield_for_dbfield(model._meta.get_field(fieldname), request=None)

        # "unwrap" the widget wrapper, if needed
        if isinstance(ff.widget, widgets.RelatedFieldWidgetWrapper):
            widget = ff.widget.widget
        else:
            widget = ff.widget

        # Check that we got a field of the right type
        self.assert_(
            isinstance(widget, widgetclass),
            "Wrong widget for %s.%s: expected %s, got %s" % \
                (model.__class__.__name__, fieldname, widgetclass, type(widget))
        )

        # Return the formfield so that other tests can continue
        return ff

    def testDateField(self):
        self.assertFormfield(models.Event, 'start_date', widgets.AdminDateWidget)

    def testDateTimeField(self):
        self.assertFormfield(models.Member, 'birthdate', widgets.AdminSplitDateTime)

    def testTimeField(self):
        self.assertFormfield(models.Event, 'start_time', widgets.AdminTimeWidget)

    def testTextField(self):
        self.assertFormfield(models.Event, 'description', widgets.AdminTextareaWidget)

    def testURLField(self):
        self.assertFormfield(models.Event, 'link', widgets.AdminURLFieldWidget)

    def testIntegerField(self):
        self.assertFormfield(models.Event, 'min_age', widgets.AdminIntegerFieldWidget)

    def testCharField(self):
        self.assertFormfield(models.Member, 'name', widgets.AdminTextInputWidget)

    def testFileField(self):
        self.assertFormfield(models.Album, 'cover_art', widgets.AdminFileWidget)

    def testForeignKey(self):
        self.assertFormfield(models.Event, 'band', forms.Select)

    def testRawIDForeignKey(self):
        self.assertFormfield(models.Event, 'band', widgets.ForeignKeyRawIdWidget,
                             raw_id_fields=['band'])

    def testRadioFieldsForeignKey(self):
        ff = self.assertFormfield(models.Event, 'band', widgets.AdminRadioSelect,
                                  radio_fields={'band':admin.VERTICAL})
        self.assertEqual(ff.empty_label, None)

    def testManyToMany(self):
        self.assertFormfield(models.Band, 'members', forms.SelectMultiple)

    def testRawIDManyTOMany(self):
        self.assertFormfield(models.Band, 'members', widgets.ManyToManyRawIdWidget,
                             raw_id_fields=['members'])

    def testFilteredManyToMany(self):
        self.assertFormfield(models.Band, 'members', widgets.FilteredSelectMultiple,
                             filter_vertical=['members'])

    def testFormfieldOverrides(self):
        self.assertFormfield(models.Event, 'start_date', forms.TextInput,
                             formfield_overrides={'widget': forms.TextInput})

    def testFieldWithChoices(self):
        self.assertFormfield(models.Member, 'gender', forms.Select)

    def testChoicesWithRadioFields(self):
        self.assertFormfield(models.Member, 'gender', widgets.AdminRadioSelect,
                             radio_fields={'gender':admin.VERTICAL})

    def testInheritance(self):
        self.assertFormfield(models.Album, 'backside_art', widgets.AdminFileWidget)

class AdminFormfieldForDBFieldWithRequestTests(DjangoTestCase):
    fixtures = ["admin-widgets-users.xml"]

    def testFilterChoicesByRequestUser(self):
        """
        Ensure the user can only see their own cars in the foreign key dropdown.
        """
        self.client.login(username="super", password="secret")
        response = self.client.get("/widget_admin/admin_widgets/cartire/add/")
        self.assert_("BMW M3" not in response.content)
        self.assert_("Volkswagon Passat" in response.content)

class AdminForeignKeyWidgetChangeList(DjangoTestCase):
    fixtures = ["admin-widgets-users.xml"]

    def setUp(self):
        self.client.login(username="super", password="secret")

    def tearDown(self):
        self.client.logout()

    def test_changelist_foreignkey(self):
        response = self.client.get('/widget_admin/admin_widgets/car/')
        self.failUnless('/widget_admin/auth/user/add/' in response.content)
