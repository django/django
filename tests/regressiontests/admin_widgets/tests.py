# encoding: utf-8
from __future__ import with_statement, absolute_import

from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import DateField
from django.test import TestCase as DjangoTestCase
from django.utils import translation
from django.utils.html import conditional_escape
from django.utils.unittest import TestCase

from . import models
from .widgetadmin import site as widget_admin_site


admin_media_prefix = lambda: {
    'ADMIN_MEDIA_PREFIX': "%sadmin/" % settings.STATIC_URL,
}

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
        self.assertTrue(
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
        self.assertTrue("BMW M3" not in response.content)
        self.assertTrue("Volkswagon Passat" in response.content)


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

    def test_url_params_from_lookup_dict_any_iterable(self):
        lookup1 = widgets.url_params_from_lookup_dict({'color__in': ('red', 'blue')})
        lookup2 = widgets.url_params_from_lookup_dict({'color__in': ['red', 'blue']})
        self.assertEqual(lookup1, {'color__in': 'red,blue'})
        self.assertEqual(lookup1, lookup2)


class FilteredSelectMultipleWidgetTest(DjangoTestCase):
    def test_render(self):
        w = widgets.FilteredSelectMultiple('test', False)
        self.assertHTMLEqual(
            conditional_escape(w.render('test', 'test')),
            '<select multiple="multiple" name="test" class="selectfilter">\n</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 0, "%(ADMIN_MEDIA_PREFIX)s"); });</script>\n' % admin_media_prefix()
        )

    def test_stacked_render(self):
        w = widgets.FilteredSelectMultiple('test', True)
        self.assertHTMLEqual(
            conditional_escape(w.render('test', 'test')),
            '<select multiple="multiple" name="test" class="selectfilterstacked">\n</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 1, "%(ADMIN_MEDIA_PREFIX)s"); });</script>\n' % admin_media_prefix()
        )

class AdminDateWidgetTest(DjangoTestCase):
    def test_attrs(self):
        """
        Ensure that user-supplied attrs are used.
        Refs #12073.
        """
        w = widgets.AdminDateWidget()
        self.assertHTMLEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<input value="2007-12-01" type="text" class="vDateField" name="test" size="10" />',
        )
        # pass attrs to widget
        w = widgets.AdminDateWidget(attrs={'size': 20, 'class': 'myDateField'})
        self.assertHTMLEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<input value="2007-12-01" type="text" class="myDateField" name="test" size="20" />',
        )

class AdminTimeWidgetTest(DjangoTestCase):
    def test_attrs(self):
        """
        Ensure that user-supplied attrs are used.
        Refs #12073.
        """
        w = widgets.AdminTimeWidget()
        self.assertHTMLEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<input value="09:30:00" type="text" class="vTimeField" name="test" size="8" />',
        )
        # pass attrs to widget
        w = widgets.AdminTimeWidget(attrs={'size': 20, 'class': 'myTimeField'})
        self.assertHTMLEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<input value="09:30:00" type="text" class="myTimeField" name="test" size="20" />',
        )

class AdminSplitDateTimeWidgetTest(DjangoTestCase):
    def test_render(self):
        w = widgets.AdminSplitDateTime()
        self.assertHTMLEqual(
            conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
            '<p class="datetime">Date: <input value="2007-12-01" type="text" class="vDateField" name="test_0" size="10" /><br />Time: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>',
        )

    def test_localization(self):
        w = widgets.AdminSplitDateTime()

        with self.settings(USE_L10N=True):
            with translation.override('de-at'):
                w.is_localized = True
                self.assertHTMLEqual(
                    conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30))),
                    '<p class="datetime">Datum: <input value="01.12.2007" type="text" class="vDateField" name="test_0" size="10" /><br />Zeit: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>',
                )


class AdminFileWidgetTest(DjangoTestCase):
    def test_render(self):
        band = models.Band.objects.create(name='Linkin Park')
        album = band.album_set.create(
            name='Hybrid Theory', cover_art=r'albums\hybrid_theory.jpg'
        )

        w = widgets.AdminFileWidget()
        self.assertHTMLEqual(
            conditional_escape(w.render('test', album.cover_art)),
            '<p class="file-upload">Currently: <a href="%(STORAGE_URL)salbums/hybrid_theory.jpg">albums\hybrid_theory.jpg</a> <span class="clearable-file-input"><input type="checkbox" name="test-clear" id="test-clear_id" /> <label for="test-clear_id">Clear</label></span><br />Change: <input type="file" name="test" /></p>' % { 'STORAGE_URL': default_storage.url('') },
        )

        self.assertHTMLEqual(
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

        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            conditional_escape(w.render('test', band.pk, attrs={})),
            '<input type="text" name="test" value="%(bandpk)s" class="vForeignKeyRawIdAdminField" /><a href="/widget_admin/admin_widgets/band/?t=id" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Linkin Park</strong>' % dict(admin_media_prefix(), bandpk=band.pk)
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
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render('test', core.parent_id, attrs={}),
            '<input type="text" name="test" value="86" class="vForeignKeyRawIdAdminField" /><a href="/widget_admin/admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Apple</strong>' % admin_media_prefix()
        )

    def test_fk_related_model_not_in_admin(self):
        # FK to a model not registered with admin site. Raw ID widget should
        # have no magnifying glass link. See #16542
        big_honeycomb = models.Honeycomb.objects.create(location='Old tree')
        big_honeycomb.bee_set.create()
        rel = models.Bee._meta.get_field('honeycomb').rel

        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            conditional_escape(w.render('honeycomb_widget', big_honeycomb.pk, attrs={})),
            '<input type="text" name="honeycomb_widget" value="%(hcombpk)s" />&nbsp;<strong>Honeycomb object</strong>' % {'hcombpk': big_honeycomb.pk}
        )

    def test_fk_to_self_model_not_in_admin(self):
        # FK to self, not registered with admin site. Raw ID widget should have
        # no magnifying glass link. See #16542
        subject1 = models.Individual.objects.create(name='Subject #1')
        models.Individual.objects.create(name='Child', parent=subject1)
        rel = models.Individual._meta.get_field('parent').rel

        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            conditional_escape(w.render('individual_widget', subject1.pk, attrs={})),
            '<input type="text" name="individual_widget" value="%(subj1pk)s" />&nbsp;<strong>Individual object</strong>' % {'subj1pk': subject1.pk}
        )

    def test_proper_manager_for_label_lookup(self):
        # see #9258
        rel = models.Inventory._meta.get_field('parent').rel
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)

        hidden = models.Inventory.objects.create(
            barcode=93, name='Hidden', hidden=True
        )
        child_of_hidden = models.Inventory.objects.create(
            barcode=94, name='Child of hidden', parent=hidden
        )
        self.assertHTMLEqual(
            w.render('test', child_of_hidden.parent_id, attrs={}),
            '<input type="text" name="test" value="93" class="vForeignKeyRawIdAdminField" /><a href="/widget_admin/admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Hidden</strong>' % admin_media_prefix()
        )


class ManyToManyRawIdWidgetTest(DjangoTestCase):
    def test_render(self):
        band = models.Band.objects.create(name='Linkin Park')

        m1 = models.Member.objects.create(name='Chester')
        m2 = models.Member.objects.create(name='Mike')
        band.members.add(m1, m2)
        rel = models.Band._meta.get_field('members').rel

        w = widgets.ManyToManyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            conditional_escape(w.render('test', [m1.pk, m2.pk], attrs={})),
            '<input type="text" name="test" value="%(m1pk)s,%(m2pk)s" class="vManyToManyRawIdAdminField" /><a href="/widget_admin/admin_widgets/member/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="/static/admin/img/selector-search.gif" width="16" height="16" alt="Lookup" /></a>' % dict(admin_media_prefix(), m1pk=m1.pk, m2pk=m2.pk)
        )

        self.assertHTMLEqual(
            conditional_escape(w.render('test', [m1.pk])),
            '<input type="text" name="test" value="%(m1pk)s" class="vManyToManyRawIdAdminField" /><a href="/widget_admin/admin_widgets/member/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/selector-search.gif" width="16" height="16" alt="Lookup" /></a>' % dict(admin_media_prefix(), m1pk=m1.pk)
        )

        self.assertEqual(w._has_changed(None, None), False)
        self.assertEqual(w._has_changed([], None), False)
        self.assertEqual(w._has_changed(None, [u'1']), True)
        self.assertEqual(w._has_changed([1, 2], [u'1', u'2']), False)
        self.assertEqual(w._has_changed([1, 2], [u'1']), True)
        self.assertEqual(w._has_changed([1, 2], [u'1', u'3']), True)

    def test_m2m_related_model_not_in_admin(self):
        # M2M relationship with model not registered with admin site. Raw ID
        # widget should have no magnifying glass link. See #16542
        consultor1 = models.Advisor.objects.create(name='Rockstar Techie')

        c1 = models.Company.objects.create(name='Doodle')
        c2 = models.Company.objects.create(name='Pear')
        consultor1.companies.add(c1, c2)
        rel = models.Advisor._meta.get_field('companies').rel

        w = widgets.ManyToManyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            conditional_escape(w.render('company_widget1', [c1.pk, c2.pk], attrs={})),
            '<input type="text" name="company_widget1" value="%(c1pk)s,%(c2pk)s" />' % {'c1pk': c1.pk, 'c2pk': c2.pk}
        )

        self.assertHTMLEqual(
            conditional_escape(w.render('company_widget2', [c1.pk])),
            '<input type="text" name="company_widget2" value="%(c1pk)s" />' % {'c1pk': c1.pk}
        )

class RelatedFieldWidgetWrapperTests(DjangoTestCase):
    def test_no_can_add_related(self):
        rel = models.Individual._meta.get_field('parent').rel
        w = widgets.AdminRadioSelect()
        # Used to fail with a name error.
        w = widgets.RelatedFieldWidgetWrapper(w, rel, widget_admin_site)
        self.assertFalse(w.can_add_related)



class DateTimePickerSeleniumFirefoxTests(AdminSeleniumWebDriverTestCase):
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'
    fixtures = ['admin-widgets-users.xml']
    urls = "regressiontests.admin_widgets.urls"

    def test_show_hide_date_time_picker_widgets(self):
        """
        Ensure that pressing the ESC key closes the date and time picker
        widgets.
        Refs #17064.
        """
        from selenium.webdriver.common.keys import Keys

        self.admin_login(username='super', password='secret', login_url='/')
        # Open a page that has a date and time picker widgets
        self.selenium.get('%s%s' % (self.live_server_url,
            '/admin_widgets/member/add/'))

        # First, with the date picker widget ---------------------------------
        # Check that the date picker is hidden
        self.assertEqual(
            self.get_css_value('#calendarbox0', 'display'), 'none')
        # Click the calendar icon
        self.selenium.find_element_by_id('calendarlink0').click()
        # Check that the date picker is visible
        self.assertEqual(
            self.get_css_value('#calendarbox0', 'display'), 'block')
        # Press the ESC key
        self.selenium.find_element_by_tag_name('body').send_keys([Keys.ESCAPE])
        # Check that the date picker is hidden again
        self.assertEqual(
            self.get_css_value('#calendarbox0', 'display'), 'none')

        # Then, with the time picker widget ----------------------------------
        # Check that the time picker is hidden
        self.assertEqual(
            self.get_css_value('#clockbox0', 'display'), 'none')
        # Click the time icon
        self.selenium.find_element_by_id('clocklink0').click()
        # Check that the time picker is visible
        self.assertEqual(
            self.get_css_value('#clockbox0', 'display'), 'block')
        # Press the ESC key
        self.selenium.find_element_by_tag_name('body').send_keys([Keys.ESCAPE])
        # Check that the time picker is hidden again
        self.assertEqual(
            self.get_css_value('#clockbox0', 'display'), 'none')

class DateTimePickerSeleniumChromeTests(DateTimePickerSeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'

class DateTimePickerSeleniumIETests(DateTimePickerSeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'


class HorizontalVerticalFilterSeleniumFirefoxTests(AdminSeleniumWebDriverTestCase):
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'
    fixtures = ['admin-widgets-users.xml']
    urls = "regressiontests.admin_widgets.urls"

    def setUp(self):
        self.lisa = models.Student.objects.create(name='Lisa')
        self.john = models.Student.objects.create(name='John')
        self.bob = models.Student.objects.create(name='Bob')
        self.peter = models.Student.objects.create(name='Peter')
        self.jenny = models.Student.objects.create(name='Jenny')
        self.jason = models.Student.objects.create(name='Jason')
        self.cliff = models.Student.objects.create(name='Cliff')
        self.arthur = models.Student.objects.create(name='Arthur')
        self.school = models.School.objects.create(name='School of Awesome')
        super(HorizontalVerticalFilterSeleniumFirefoxTests, self).setUp()

    def assertActiveButtons(self, mode, field_name, choose, remove,
                             choose_all=None, remove_all=None):
        choose_link = '#id_%s_add_link' % field_name
        choose_all_link = '#id_%s_add_all_link' % field_name
        remove_link = '#id_%s_remove_link' % field_name
        remove_all_link = '#id_%s_remove_all_link' % field_name
        self.assertEqual(self.has_css_class(choose_link, 'active'), choose)
        self.assertEqual(self.has_css_class(remove_link, 'active'), remove)
        if mode == 'horizontal':
            self.assertEqual(self.has_css_class(choose_all_link, 'active'), choose_all)
            self.assertEqual(self.has_css_class(remove_all_link, 'active'), remove_all)

    def execute_basic_operations(self, mode, field_name):
        from_box = '#id_%s_from' % field_name
        to_box = '#id_%s_to' % field_name
        choose_link = 'id_%s_add_link' % field_name
        choose_all_link = 'id_%s_add_all_link' % field_name
        remove_link = 'id_%s_remove_link' % field_name
        remove_all_link = 'id_%s_remove_all_link' % field_name

        # Initial positions ---------------------------------------------------
        self.assertSelectOptions(from_box,
                        [str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jason.id),
                         str(self.jenny.id), str(self.john.id)])
        self.assertSelectOptions(to_box,
                        [str(self.lisa.id), str(self.peter.id)])
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        # Click 'Choose all' --------------------------------------------------
        if mode == 'horizontal':
            self.selenium.find_element_by_id(choose_all_link).click()
        elif mode == 'vertical':
            # There 's no 'Choose all' button in vertical mode, so individually
            # select all options and click 'Choose'.
            for option in self.selenium.find_elements_by_css_selector(from_box + ' > option'):
                option.click()
            self.selenium.find_element_by_id(choose_link).click()
        self.assertSelectOptions(from_box, [])
        self.assertSelectOptions(to_box,
                        [str(self.lisa.id), str(self.peter.id),
                         str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jason.id),
                         str(self.jenny.id), str(self.john.id)])
        self.assertActiveButtons(mode, field_name, False, False, False, True)

        # Click 'Remove all' --------------------------------------------------
        if mode == 'horizontal':
            self.selenium.find_element_by_id(remove_all_link).click()
        elif mode == 'vertical':
            # There 's no 'Remove all' button in vertical mode, so individually
            # select all options and click 'Remove'.
            for option in self.selenium.find_elements_by_css_selector(to_box + ' > option'):
                option.click()
            self.selenium.find_element_by_id(remove_link).click()
        self.assertSelectOptions(from_box,
                        [str(self.lisa.id), str(self.peter.id),
                         str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jason.id),
                         str(self.jenny.id), str(self.john.id)])
        self.assertSelectOptions(to_box, [])
        self.assertActiveButtons(mode, field_name, False, False, True, False)

        # Choose some options ------------------------------------------------
        self.get_select_option(from_box, str(self.lisa.id)).click()
        self.get_select_option(from_box, str(self.jason.id)).click()
        self.get_select_option(from_box, str(self.bob.id)).click()
        self.get_select_option(from_box, str(self.john.id)).click()
        self.assertActiveButtons(mode, field_name, True, False, True, False)
        self.selenium.find_element_by_id(choose_link).click()
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        self.assertSelectOptions(from_box,
                        [str(self.peter.id), str(self.arthur.id),
                         str(self.cliff.id), str(self.jenny.id)])
        self.assertSelectOptions(to_box,
                        [str(self.lisa.id), str(self.bob.id),
                         str(self.jason.id), str(self.john.id)])

        # Remove some options -------------------------------------------------
        self.get_select_option(to_box, str(self.lisa.id)).click()
        self.get_select_option(to_box, str(self.bob.id)).click()
        self.assertActiveButtons(mode, field_name, False, True, True, True)
        self.selenium.find_element_by_id(remove_link).click()
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        self.assertSelectOptions(from_box,
                        [str(self.peter.id), str(self.arthur.id),
                         str(self.cliff.id), str(self.jenny.id),
                         str(self.lisa.id), str(self.bob.id)])
        self.assertSelectOptions(to_box,
                        [str(self.jason.id), str(self.john.id)])

        # Choose some more options --------------------------------------------
        self.get_select_option(from_box, str(self.arthur.id)).click()
        self.get_select_option(from_box, str(self.cliff.id)).click()
        self.selenium.find_element_by_id(choose_link).click()

        self.assertSelectOptions(from_box,
                        [str(self.peter.id), str(self.jenny.id),
                         str(self.lisa.id), str(self.bob.id)])
        self.assertSelectOptions(to_box,
                        [str(self.jason.id), str(self.john.id),
                         str(self.arthur.id), str(self.cliff.id)])

    def test_basic(self):
        self.school.students = [self.lisa, self.peter]
        self.school.alumni = [self.lisa, self.peter]
        self.school.save()

        self.admin_login(username='super', password='secret', login_url='/')
        self.selenium.get(
            '%s%s' % (self.live_server_url, '/admin_widgets/school/%s/' % self.school.id))

        self.wait_page_loaded()
        self.execute_basic_operations('vertical', 'students')
        self.execute_basic_operations('horizontal', 'alumni')

        # Save and check that everything is properly stored in the database ---
        self.selenium.find_element_by_xpath('//input[@value="Save"]').click()
        self.wait_page_loaded()
        self.school = models.School.objects.get(id=self.school.id)  # Reload from database
        self.assertEqual(list(self.school.students.all()),
                         [self.arthur, self.cliff, self.jason, self.john])
        self.assertEqual(list(self.school.alumni.all()),
                         [self.arthur, self.cliff, self.jason, self.john])

    def test_filter(self):
        """
        Ensure that typing in the search box filters out options displayed in
        the 'from' box.
        """
        from selenium.webdriver.common.keys import Keys

        self.school.students = [self.lisa, self.peter]
        self.school.alumni = [self.lisa, self.peter]
        self.school.save()

        self.admin_login(username='super', password='secret', login_url='/')
        self.selenium.get(
            '%s%s' % (self.live_server_url, '/admin_widgets/school/%s/' % self.school.id))


        for field_name in ['students', 'alumni']:
            from_box = '#id_%s_from' % field_name
            to_box = '#id_%s_to' % field_name
            choose_link = '#id_%s_add_link' % field_name
            remove_link = '#id_%s_remove_link' % field_name
            input = self.selenium.find_element_by_css_selector('#id_%s_input' % field_name)

            # Initial values
            self.assertSelectOptions(from_box,
                        [str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jason.id),
                         str(self.jenny.id), str(self.john.id)])

            # Typing in some characters filters out non-matching options
            input.send_keys('a')
            self.assertSelectOptions(from_box, [str(self.arthur.id), str(self.jason.id)])
            input.send_keys('R')
            self.assertSelectOptions(from_box, [str(self.arthur.id)])

            # Clearing the text box makes the other options reappear
            input.send_keys([Keys.BACK_SPACE])
            self.assertSelectOptions(from_box, [str(self.arthur.id), str(self.jason.id)])
            input.send_keys([Keys.BACK_SPACE])
            self.assertSelectOptions(from_box,
                        [str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jason.id),
                         str(self.jenny.id), str(self.john.id)])

            # -----------------------------------------------------------------
            # Check that chosing a filtered option sends it properly to the
            # 'to' box.
            input.send_keys('a')
            self.assertSelectOptions(from_box, [str(self.arthur.id), str(self.jason.id)])
            self.get_select_option(from_box, str(self.jason.id)).click()
            self.selenium.find_element_by_css_selector(choose_link).click()
            self.assertSelectOptions(from_box, [str(self.arthur.id)])
            self.assertSelectOptions(to_box,
                        [str(self.lisa.id), str(self.peter.id),
                         str(self.jason.id)])

            self.get_select_option(to_box, str(self.lisa.id)).click()
            self.selenium.find_element_by_css_selector(remove_link).click()
            self.assertSelectOptions(from_box,
                        [str(self.arthur.id), str(self.lisa.id)])
            self.assertSelectOptions(to_box,
                        [str(self.peter.id), str(self.jason.id)])

            input.send_keys([Keys.BACK_SPACE]) # Clear text box
            self.assertSelectOptions(from_box,
                        [str(self.arthur.id), str(self.bob.id),
                         str(self.cliff.id), str(self.jenny.id),
                         str(self.john.id), str(self.lisa.id)])
            self.assertSelectOptions(to_box,
                        [str(self.peter.id), str(self.jason.id)])

        # Save and check that everything is properly stored in the database ---
        self.selenium.find_element_by_xpath('//input[@value="Save"]').click()
        self.wait_page_loaded()
        self.school = models.School.objects.get(id=self.school.id) # Reload from database
        self.assertEqual(list(self.school.students.all()),
                         [self.jason, self.peter])
        self.assertEqual(list(self.school.alumni.all()),
                         [self.jason, self.peter])

class HorizontalVerticalFilterSeleniumChromeTests(HorizontalVerticalFilterSeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'

class HorizontalVerticalFilterSeleniumIETests(HorizontalVerticalFilterSeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'
