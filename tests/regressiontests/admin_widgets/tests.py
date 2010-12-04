# encoding: utf-8

from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.admin.widgets import (FilteredSelectMultiple,
    AdminSplitDateTime, AdminFileWidget, ForeignKeyRawIdWidget, AdminRadioSelect,
    RelatedFieldWidgetWrapper, ManyToManyRawIdWidget)
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import DateField
from django.test import TestCase as DjangoTestCase
from django.utils.html import conditional_escape
from django.utils.translation import activate, deactivate
from django.utils.unittest import TestCase

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
        class MyModelAdmin(admin.ModelAdmin):
            pass
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
                             formfield_overrides={DateField: {'widget': forms.TextInput}})

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
    admin_root = '/widget_admin'

    def setUp(self):
        self.client.login(username="super", password="secret")

    def tearDown(self):
        self.client.logout()

    def test_changelist_foreignkey(self):
        response = self.client.get('%s/admin_widgets/car/' % self.admin_root)
        self.assertTrue('%s/auth/user/add/' % self.admin_root in response.content)


class AdminForeignKeyRawIdWidget(DjangoTestCase):
    fixtures = ["admin-widgets-users.xml"]
    admin_root = '/widget_admin'

    def setUp(self):
        self.client.login(username="super", password="secret")

    def tearDown(self):
        self.client.logout()

    def test_nonexistent_target_id(self):
        band = models.Band.objects.create(name='Bogey Blues')
        pk = band.pk
        band.delete()
        post_data = {
            "band": u'%s' % pk,
        }
        # Try posting with a non-existent pk in a raw id field: this
        # should result in an error message, not a server exception.
        response = self.client.post('%s/admin_widgets/event/add/' % self.admin_root,
            post_data)
        self.assertContains(response,
            'Select a valid choice. That choice is not one of the available choices.')

    def test_invalid_target_id(self):

        for test_str in ('Iñtërnâtiônàlizætiøn', "1234'", -1234):
            # This should result in an error message, not a server exception.
            response = self.client.post('%s/admin_widgets/event/add/' % self.admin_root,
                {"band": test_str})

            self.assertContains(response,
                'Select a valid choice. That choice is not one of the available choices.')


class FilteredSelectMultipleWidgetTest(TestCase):
    def test_render(self):
        w = FilteredSelectMultiple('test', False)
        self.assertEqual(
            conditional_escape(w.render('test', 'test')),
            '<select multiple="multiple" name="test" class="selectfilter">\n</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 0, "%(ADMIN_MEDIA_PREFIX)s"); });</script>\n' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX}
        )

    def test_stacked_render(self):
        w = FilteredSelectMultiple('test', True)
        self.assertEqual(
            conditional_escape(w.render('test', 'test')),
            '<select multiple="multiple" name="test" class="selectfilterstacked">\n</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 1, "%(ADMIN_MEDIA_PREFIX)s"); });</script>\n' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX}
        )


class AdminSplitDateTimeWidgetTest(TestCase):
    def test_render(self):
        w = AdminSplitDateTime()
        self.assertEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<p class="datetime">Date: <input value="2007-12-01" type="text" class="vDateField" name="test_0" size="10" /><br />Time: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>',
        )

    def test_localization(self):
        w = AdminSplitDateTime()

        activate('de-at')
        old_USE_L10N = settings.USE_L10N
        settings.USE_L10N = True
        w.is_localized = True
        self.assertEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<p class="datetime">Datum: <input value="01.12.2007" type="text" class="vDateField" name="test_0" size="10" /><br />Zeit: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>',
        )
        deactivate()
        settings.USE_L10N = old_USE_L10N


class AdminFileWidgetTest(DjangoTestCase):
    def test_render(self):
        band = models.Band.objects.create(name='Linkin Park')
        album = band.album_set.create(
            name='Hybrid Theory', cover_art=r'albums\hybrid_theory.jpg'
        )

        w = AdminFileWidget()
        self.assertEqual(
            conditional_escape(w.render('test', album.cover_art)),
            '<p class="file-upload">Currently: <a target="_blank" href="%(STORAGE_URL)salbums/hybrid_theory.jpg">albums\hybrid_theory.jpg</a> <span class="clearable-file-input"><input type="checkbox" name="test-clear" id="test-clear_id" /> <label for="test-clear_id">Clear</label></span><br />Change: <input type="file" name="test" /></p>' % { 'STORAGE_URL': default_storage.url('') },
        )

        self.assertEqual(
            conditional_escape(w.render('test', SimpleUploadedFile('test', 'content'))),
            '<input type="file" name="test" />',
        )


class ForeignKeyRawIdWidgetTest(DjangoTestCase):
    def test_render(self):
        band = models.Band.objects.create(name='Linkin Park')
        band.album_set.create(
            name='Hybrid Theory', cover_art=r'albums\hybrid_theory.jpg'
        )
        rel = models.Album._meta.get_field('band').rel

        w = ForeignKeyRawIdWidget(rel)
        self.assertEqual(
            conditional_escape(w.render('test', band.pk, attrs={})),
            '<input type="text" name="test" value="%(bandpk)s" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/band/?t=id" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Linkin Park</strong>' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX, "bandpk": band.pk},
        )

    def test_relations_to_non_primary_key(self):
        # Check that ForeignKeyRawIdWidget works with fields which aren't
        # related to the model's primary key.
        apple = models.Inventory.objects.create(barcode=86, name='Apple')
        models.Inventory.objects.create(barcode=22, name='Pear')
        core = models.Inventory.objects.create(
            barcode=87, name='Core', parent=apple
        )
        rel = models.Inventory._meta.get_field('parent').rel
        w = ForeignKeyRawIdWidget(rel)
        self.assertEqual(
            w.render('test', core.parent_id, attrs={}),
            '<input type="text" name="test" value="86" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Apple</strong>' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX},
        )


    def test_proper_manager_for_label_lookup(self):
        # see #9258
        rel = models.Inventory._meta.get_field('parent').rel
        w = ForeignKeyRawIdWidget(rel)

        hidden = models.Inventory.objects.create(
            barcode=93, name='Hidden', hidden=True
        )
        child_of_hidden = models.Inventory.objects.create(
            barcode=94, name='Child of hidden', parent=hidden
        )
        self.assertEqual(
            w.render('test', child_of_hidden.parent_id, attrs={}),
            '<input type="text" name="test" value="93" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Hidden</strong>' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX},
        )


class ManyToManyRawIdWidgetTest(DjangoTestCase):
    def test_render(self):
        band = models.Band.objects.create(name='Linkin Park')
        band.album_set.create(
            name='Hybrid Theory', cover_art=r'albums\hybrid_theory.jpg'
        )

        m1 = models.Member.objects.create(name='Chester')
        m2 = models.Member.objects.create(name='Mike')
        band.members.add(m1, m2)
        rel = models.Band._meta.get_field('members').rel

        w = ManyToManyRawIdWidget(rel)
        self.assertEqual(
            conditional_escape(w.render('test', [m1.pk, m2.pk], attrs={})),
            '<input type="text" name="test" value="%(m1pk)s,%(m2pk)s" class="vManyToManyRawIdAdminField" /><a href="../../../admin_widgets/member/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX, "m1pk": m1.pk, "m2pk": m2.pk},
        )

        self.assertEqual(
            conditional_escape(w.render('test', [m1.pk])),
            '<input type="text" name="test" value="%(m1pk)s" class="vManyToManyRawIdAdminField" /><a href="../../../admin_widgets/member/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>' % {"ADMIN_MEDIA_PREFIX": settings.ADMIN_MEDIA_PREFIX, "m1pk": m1.pk},
        )

        self.assertEqual(w._has_changed(None, None), False)
        self.assertEqual(w._has_changed([], None), False)
        self.assertEqual(w._has_changed(None, [u'1']), True)
        self.assertEqual(w._has_changed([1, 2], [u'1', u'2']), False)
        self.assertEqual(w._has_changed([1, 2], [u'1']), True)
        self.assertEqual(w._has_changed([1, 2], [u'1', u'3']), True)

class RelatedFieldWidgetWrapperTests(DjangoTestCase):
    def test_no_can_add_related(self):
        rel = models.Inventory._meta.get_field('parent').rel
        w = AdminRadioSelect()
        # Used to fail with a name error.
        w = RelatedFieldWidgetWrapper(w, rel, admin.site)
        self.assertFalse(w.can_add_related)
