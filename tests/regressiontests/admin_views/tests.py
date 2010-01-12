# coding: utf-8

import re
import datetime
from django.core.files import temp as tempfile
from django.test import TestCase
from django.contrib.auth import admin # Register auth models with the admin.
from django.contrib.auth.models import User, Permission, UNUSABLE_PASSWORD
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.admin.sites import LOGIN_FORM_KEY
from django.contrib.admin.util import quote
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.utils import formats
from django.utils.cache import get_max_age
from django.utils.html import escape
from django.utils.translation import get_date_formats

# local test models
from models import Article, BarAccount, CustomArticle, EmptyModel, \
    ExternalSubscriber, FooAccount, Gallery, ModelWithStringPrimaryKey, \
    Person, Persona, Picture, Podcast, Section, Subscriber, Vodcast, \
    Language, Collector, Widget, Grommet, DooHickey, FancyDoodad, Whatsit, \
    Category, Post


class AdminViewBasicTest(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-colors.xml', 'admin-views-fabrics.xml']

    # Store the bit of the URL where the admin is registered as a class
    # variable. That way we can test a second AdminSite just by subclassing
    # this test case and changing urlbit.
    urlbit = 'admin'

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testTrailingSlashRequired(self):
        """
        If you leave off the trailing slash, app should redirect and add it.
        """
        request = self.client.get('/test_admin/%s/admin_views/article/add' % self.urlbit)
        self.assertRedirects(request,
            '/test_admin/%s/admin_views/article/add/' % self.urlbit, status_code=301
        )

    def testBasicAddGet(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get('/test_admin/%s/admin_views/section/add/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)

    def testAddWithGETArgs(self):
        response = self.client.get('/test_admin/%s/admin_views/section/add/' % self.urlbit, {'name': 'My Section'})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            'value="My Section"' in response.content,
            "Couldn't find an input with the right value in the response."
        )

    def testBasicEditGet(self):
        """
        A smoke test to ensure GET on the change_view works.
        """
        response = self.client.get('/test_admin/%s/admin_views/section/1/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)

    def testBasicEditGetStringPK(self):
        """
        A smoke test to ensure GET on the change_view works (returns an HTTP
        404 error, see #11191) when passing a string as the PK argument for a
        model with an integer PK field.
        """
        response = self.client.get('/test_admin/%s/admin_views/section/abc/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 404)

    def testBasicAddPost(self):
        """
        A smoke test to ensure POST on add_view works.
        """
        post_data = {
            "name": u"Another Section",
            # inline data
            "article_set-TOTAL_FORMS": u"3",
            "article_set-INITIAL_FORMS": u"0",
        }
        response = self.client.post('/test_admin/%s/admin_views/section/add/' % self.urlbit, post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

    # Post data for edit inline
    inline_post_data = {
        "name": u"Test section",
        # inline data
        "article_set-TOTAL_FORMS": u"6",
        "article_set-INITIAL_FORMS": u"3",
        "article_set-0-id": u"1",
        # there is no title in database, give one here or formset will fail.
        "article_set-0-title": u"Norske bostaver æøå skaper problemer",
        "article_set-0-content": u"&lt;p&gt;Middle content&lt;/p&gt;",
        "article_set-0-date_0": u"2008-03-18",
        "article_set-0-date_1": u"11:54:58",
        "article_set-0-section": u"1",
        "article_set-1-id": u"2",
        "article_set-1-title": u"Need a title.",
        "article_set-1-content": u"&lt;p&gt;Oldest content&lt;/p&gt;",
        "article_set-1-date_0": u"2000-03-18",
        "article_set-1-date_1": u"11:54:58",
        "article_set-2-id": u"3",
        "article_set-2-title": u"Need a title.",
        "article_set-2-content": u"&lt;p&gt;Newest content&lt;/p&gt;",
        "article_set-2-date_0": u"2009-03-18",
        "article_set-2-date_1": u"11:54:58",
        "article_set-3-id": u"",
        "article_set-3-title": u"",
        "article_set-3-content": u"",
        "article_set-3-date_0": u"",
        "article_set-3-date_1": u"",
        "article_set-4-id": u"",
        "article_set-4-title": u"",
        "article_set-4-content": u"",
        "article_set-4-date_0": u"",
        "article_set-4-date_1": u"",
        "article_set-5-id": u"",
        "article_set-5-title": u"",
        "article_set-5-content": u"",
        "article_set-5-date_0": u"",
        "article_set-5-date_1": u"",
    }

    def testBasicEditPost(self):
        """
        A smoke test to ensure POST on edit_view works.
        """
        response = self.client.post('/test_admin/%s/admin_views/section/1/' % self.urlbit, self.inline_post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

    def testEditSaveAs(self):
        """
        Test "save as".
        """
        post_data = self.inline_post_data.copy()
        post_data.update({
            '_saveasnew': u'Save+as+new',
            "article_set-1-section": u"1",
            "article_set-2-section": u"1",
            "article_set-3-section": u"1",
            "article_set-4-section": u"1",
            "article_set-5-section": u"1",
        })
        response = self.client.post('/test_admin/%s/admin_views/section/1/' % self.urlbit, post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

    def testChangeListSortingCallable(self):
        """
        Ensure we can sort on a list_display field that is a callable
        (column 2 is callable_year in ArticleAdmin)
        """
        response = self.client.get('/test_admin/%s/admin_views/article/' % self.urlbit, {'ot': 'asc', 'o': 2})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            response.content.index('Oldest content') < response.content.index('Middle content') and
            response.content.index('Middle content') < response.content.index('Newest content'),
            "Results of sorting on callable are out of order."
        )

    def testChangeListSortingModel(self):
        """
        Ensure we can sort on a list_display field that is a Model method
        (colunn 3 is 'model_year' in ArticleAdmin)
        """
        response = self.client.get('/test_admin/%s/admin_views/article/' % self.urlbit, {'ot': 'dsc', 'o': 3})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            response.content.index('Newest content') < response.content.index('Middle content') and
            response.content.index('Middle content') < response.content.index('Oldest content'),
            "Results of sorting on Model method are out of order."
        )

    def testChangeListSortingModelAdmin(self):
        """
        Ensure we can sort on a list_display field that is a ModelAdmin method
        (colunn 4 is 'modeladmin_year' in ArticleAdmin)
        """
        response = self.client.get('/test_admin/%s/admin_views/article/' % self.urlbit, {'ot': 'asc', 'o': 4})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            response.content.index('Oldest content') < response.content.index('Middle content') and
            response.content.index('Middle content') < response.content.index('Newest content'),
            "Results of sorting on ModelAdmin method are out of order."
        )

    def testLimitedFilter(self):
        """Ensure admin changelist filters do not contain objects excluded via limit_choices_to."""
        response = self.client.get('/test_admin/%s/admin_views/thing/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            '<div id="changelist-filter">' in response.content,
            "Expected filter not found in changelist view."
        )
        self.failIf(
            '<a href="?color__id__exact=3">Blue</a>' in response.content,
            "Changelist filter not correctly limited by limit_choices_to."
        )

    def testIncorrectLookupParameters(self):
        """Ensure incorrect lookup parameters are handled gracefully."""
        response = self.client.get('/test_admin/%s/admin_views/thing/' % self.urlbit, {'notarealfield': '5'})
        self.assertRedirects(response, '/test_admin/%s/admin_views/thing/?e=1' % self.urlbit)
        response = self.client.get('/test_admin/%s/admin_views/thing/' % self.urlbit, {'color__id__exact': 'StringNotInteger!'})
        self.assertRedirects(response, '/test_admin/%s/admin_views/thing/?e=1' % self.urlbit)

    def testLogoutAndPasswordChangeURLs(self):
        response = self.client.get('/test_admin/%s/admin_views/article/' % self.urlbit)
        self.failIf('<a href="/test_admin/%s/logout/">' % self.urlbit not in response.content)
        self.failIf('<a href="/test_admin/%s/password_change/">' % self.urlbit not in response.content)

    def testNamedGroupFieldChoicesChangeList(self):
        """
        Ensures the admin changelist shows correct values in the relevant column
        for rows corresponding to instances of a model in which a named group
        has been used in the choices option of a field.
        """
        response = self.client.get('/test_admin/%s/admin_views/fabric/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            '<a href="1/">Horizontal</a>' in response.content and
            '<a href="2/">Vertical</a>' in response.content,
            "Changelist table isn't showing the right human-readable values set by a model field 'choices' option named group."
        )

    def testNamedGroupFieldChoicesFilter(self):
        """
        Ensures the filter UI shows correctly when at least one named group has
        been used in the choices option of a model field.
        """
        response = self.client.get('/test_admin/%s/admin_views/fabric/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            '<div id="changelist-filter">' in response.content,
            "Expected filter not found in changelist view."
        )
        self.failUnless(
            '<a href="?surface__exact=x">Horizontal</a>' in response.content and
            '<a href="?surface__exact=y">Vertical</a>' in response.content,
            "Changelist filter isn't showing options contained inside a model field 'choices' option named group."
        )

class SaveAsTests(TestCase):
    fixtures = ['admin-views-users.xml','admin-views-person.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_save_as_duplication(self):
        """Ensure save as actually creates a new person"""
        post_data = {'_saveasnew':'', 'name':'John M', 'gender':1}
        response = self.client.post('/test_admin/admin/admin_views/person/1/', post_data)
        self.assertEqual(len(Person.objects.filter(name='John M')), 1)
        self.assertEqual(len(Person.objects.filter(id=1)), 1)

    def test_save_as_display(self):
        """
        Ensure that 'save as' is displayed when activated and after submitting
        invalid data aside save_as_new will not show us a form to overwrite the
        initial model.
        """
        response = self.client.get('/test_admin/admin/admin_views/person/1/')
        self.assert_(response.context['save_as'])
        post_data = {'_saveasnew':'', 'name':'John M', 'gender':3, 'alive':'checked'}
        response = self.client.post('/test_admin/admin/admin_views/person/1/', post_data)
        self.assertEqual(response.context['form_url'], '../add/')

class CustomModelAdminTest(AdminViewBasicTest):
    urlbit = "admin2"

    def testCustomAdminSiteLoginTemplate(self):
        self.client.logout()
        request = self.client.get('/test_admin/admin2/')
        self.assertTemplateUsed(request, 'custom_admin/login.html')
        self.assert_('Hello from a custom login template' in request.content)

    def testCustomAdminSiteLogoutTemplate(self):
        request = self.client.get('/test_admin/admin2/logout/')
        self.assertTemplateUsed(request, 'custom_admin/logout.html')
        self.assert_('Hello from a custom logout template' in request.content)

    def testCustomAdminSiteIndexViewAndTemplate(self):
        request = self.client.get('/test_admin/admin2/')
        self.assertTemplateUsed(request, 'custom_admin/index.html')
        self.assert_('Hello from a custom index template *bar*' in request.content)

    def testCustomAdminSitePasswordChangeTemplate(self):
        request = self.client.get('/test_admin/admin2/password_change/')
        self.assertTemplateUsed(request, 'custom_admin/password_change_form.html')
        self.assert_('Hello from a custom password change form template' in request.content)

    def testCustomAdminSitePasswordChangeDoneTemplate(self):
        request = self.client.get('/test_admin/admin2/password_change/done/')
        self.assertTemplateUsed(request, 'custom_admin/password_change_done.html')
        self.assert_('Hello from a custom password change done template' in request.content)

    def testCustomAdminSiteView(self):
        self.client.login(username='super', password='secret')
        response = self.client.get('/test_admin/%s/my_view/' % self.urlbit)
        self.assert_(response.content == "Django is a magical pony!", response.content)

def get_perm(Model, perm):
    """Return the permission object, for the Model"""
    ct = ContentType.objects.get_for_model(Model)
    return Permission.objects.get(content_type=ct, codename=perm)

class AdminViewPermissionsTest(TestCase):
    """Tests for Admin Views Permissions."""

    fixtures = ['admin-views-users.xml']

    def setUp(self):
        """Test setup."""
        # Setup permissions, for our users who can add, change, and delete.
        # We can't put this into the fixture, because the content type id
        # and the permission id could be different on each run of the test.

        opts = Article._meta

        # User who can add Articles
        add_user = User.objects.get(username='adduser')
        add_user.user_permissions.add(get_perm(Article,
            opts.get_add_permission()))

        # User who can change Articles
        change_user = User.objects.get(username='changeuser')
        change_user.user_permissions.add(get_perm(Article,
            opts.get_change_permission()))

        # User who can delete Articles
        delete_user = User.objects.get(username='deleteuser')
        delete_user.user_permissions.add(get_perm(Article,
            opts.get_delete_permission()))

        delete_user.user_permissions.add(get_perm(Section,
            Section._meta.get_delete_permission()))

        # login POST dicts
        self.super_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'super',
                     'password': 'secret'}
        self.super_email_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'super@example.com',
                     'password': 'secret'}
        self.super_email_bad_login = {
                      LOGIN_FORM_KEY: 1,
                      'username': 'super@example.com',
                      'password': 'notsecret'}
        self.adduser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'adduser',
                     'password': 'secret'}
        self.changeuser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'changeuser',
                     'password': 'secret'}
        self.deleteuser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'deleteuser',
                     'password': 'secret'}
        self.joepublic_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'joepublic',
                     'password': 'secret'}
        self.no_username_login = {
                     LOGIN_FORM_KEY: 1,
                     'password': 'secret'}

    def testLogin(self):
        """
        Make sure only staff members can log in.

        Successful posts to the login page will redirect to the orignal url.
        Unsuccessfull attempts will continue to render the login page with
        a 200 status code.
        """
        # Super User
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.super_login)
        self.assertRedirects(login, '/test_admin/admin/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Test if user enters e-mail address
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.super_email_login)
        self.assertContains(login, "Your e-mail address is not your username")
        # only correct passwords get a username hint
        login = self.client.post('/test_admin/admin/', self.super_email_bad_login)
        self.assertContains(login, "Usernames cannot contain the &#39;@&#39; character")
        new_user = User(username='jondoe', password='secret', email='super@example.com')
        new_user.save()
        # check to ensure if there are multiple e-mail addresses a user doesn't get a 500
        login = self.client.post('/test_admin/admin/', self.super_email_login)
        self.assertContains(login, "Usernames cannot contain the &#39;@&#39; character")

        # Add User
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.adduser_login)
        self.assertRedirects(login, '/test_admin/admin/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Change User
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.changeuser_login)
        self.assertRedirects(login, '/test_admin/admin/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Delete User
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.deleteuser_login)
        self.assertRedirects(login, '/test_admin/admin/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Regular User should not be able to login.
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.joepublic_login)
        self.failUnlessEqual(login.status_code, 200)
        # Login.context is a list of context dicts we just need to check the first one.
        self.assert_(login.context[0].get('error_message'))

        # Requests without username should not return 500 errors.
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/', self.no_username_login)
        self.failUnlessEqual(login.status_code, 200)
        # Login.context is a list of context dicts we just need to check the first one.
        self.assert_(login.context[0].get('error_message'))

    def testLoginSuccessfullyRedirectsToOriginalUrl(self):
        request = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(request.status_code, 200)
        query_string = "the-answer=42"
        login = self.client.post('/test_admin/admin/', self.super_login, QUERY_STRING = query_string )
        self.assertRedirects(login, '/test_admin/admin/?%s' % query_string)

    def testAddView(self):
        """Test add view restricts access and actually adds items."""

        add_dict = {'title' : 'Døm ikke',
                    'content': '<p>great article</p>',
                    'date_0': '2008-03-18', 'date_1': '10:54:39',
                    'section': 1}

        # Change User should not have access to add articles
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.changeuser_login)
        # make sure the view removes test cookie
        self.failUnlessEqual(self.client.session.test_cookie_worked(), False)
        request = self.client.get('/test_admin/admin/admin_views/article/add/')
        self.failUnlessEqual(request.status_code, 403)
        # Try POST just to make sure
        post = self.client.post('/test_admin/admin/admin_views/article/add/', add_dict)
        self.failUnlessEqual(post.status_code, 403)
        self.failUnlessEqual(Article.objects.all().count(), 3)
        self.client.get('/test_admin/admin/logout/')

        # Add user may login and POST to add view, then redirect to admin root
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.adduser_login)
        addpage = self.client.get('/test_admin/admin/admin_views/article/add/')
        self.failUnlessEqual(addpage.status_code, 200)
        change_list_link = '<a href="../">Articles</a> &rsaquo;'
        self.failIf(change_list_link in addpage.content,
                    'User restricted to add permission is given link to change list view in breadcrumbs.')
        post = self.client.post('/test_admin/admin/admin_views/article/add/', add_dict)
        self.assertRedirects(post, '/test_admin/admin/')
        self.failUnlessEqual(Article.objects.all().count(), 4)
        self.client.get('/test_admin/admin/logout/')

        # Super can add too, but is redirected to the change list view
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.super_login)
        addpage = self.client.get('/test_admin/admin/admin_views/article/add/')
        self.failUnlessEqual(addpage.status_code, 200)
        self.failIf(change_list_link not in addpage.content,
                    'Unrestricted user is not given link to change list view in breadcrumbs.')
        post = self.client.post('/test_admin/admin/admin_views/article/add/', add_dict)
        self.assertRedirects(post, '/test_admin/admin/admin_views/article/')
        self.failUnlessEqual(Article.objects.all().count(), 5)
        self.client.get('/test_admin/admin/logout/')

        # 8509 - if a normal user is already logged in, it is possible
        # to change user into the superuser without error
        login = self.client.login(username='joepublic', password='secret')
        # Check and make sure that if user expires, data still persists
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.super_login)
        # make sure the view removes test cookie
        self.failUnlessEqual(self.client.session.test_cookie_worked(), False)

    def testChangeView(self):
        """Change view should restrict access and allow users to edit items."""

        change_dict = {'title' : 'Ikke fordømt',
                       'content': '<p>edited article</p>',
                       'date_0': '2008-03-18', 'date_1': '10:54:39',
                       'section': 1}

        # add user shoud not be able to view the list of article or change any of them
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.adduser_login)
        request = self.client.get('/test_admin/admin/admin_views/article/')
        self.failUnlessEqual(request.status_code, 403)
        request = self.client.get('/test_admin/admin/admin_views/article/1/')
        self.failUnlessEqual(request.status_code, 403)
        post = self.client.post('/test_admin/admin/admin_views/article/1/', change_dict)
        self.failUnlessEqual(post.status_code, 403)
        self.client.get('/test_admin/admin/logout/')

        # change user can view all items and edit them
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.changeuser_login)
        request = self.client.get('/test_admin/admin/admin_views/article/')
        self.failUnlessEqual(request.status_code, 200)
        request = self.client.get('/test_admin/admin/admin_views/article/1/')
        self.failUnlessEqual(request.status_code, 200)
        post = self.client.post('/test_admin/admin/admin_views/article/1/', change_dict)
        self.assertRedirects(post, '/test_admin/admin/admin_views/article/')
        self.failUnlessEqual(Article.objects.get(pk=1).content, '<p>edited article</p>')

        # one error in form should produce singular error message, multiple errors plural
        change_dict['title'] = ''
        post = self.client.post('/test_admin/admin/admin_views/article/1/', change_dict)
        self.failUnlessEqual(request.status_code, 200)
        self.failUnless('Please correct the error below.' in post.content,
                        'Singular error message not found in response to post with one error.')
        change_dict['content'] = ''
        post = self.client.post('/test_admin/admin/admin_views/article/1/', change_dict)
        self.failUnlessEqual(request.status_code, 200)
        self.failUnless('Please correct the errors below.' in post.content,
                        'Plural error message not found in response to post with multiple errors.')
        self.client.get('/test_admin/admin/logout/')

    def testCustomModelAdminTemplates(self):
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.super_login)

        # Test custom change list template with custom extra context
        request = self.client.get('/test_admin/admin/admin_views/customarticle/')
        self.failUnlessEqual(request.status_code, 200)
        self.assert_("var hello = 'Hello!';" in request.content)
        self.assertTemplateUsed(request, 'custom_admin/change_list.html')

        # Test custom add form template
        request = self.client.get('/test_admin/admin/admin_views/customarticle/add/')
        self.assertTemplateUsed(request, 'custom_admin/add_form.html')

        # Add an article so we can test delete, change, and history views
        post = self.client.post('/test_admin/admin/admin_views/customarticle/add/', {
            'content': '<p>great article</p>',
            'date_0': '2008-03-18',
            'date_1': '10:54:39'
        })
        self.assertRedirects(post, '/test_admin/admin/admin_views/customarticle/')
        self.failUnlessEqual(CustomArticle.objects.all().count(), 1)

        # Test custom delete, change, and object history templates
        # Test custom change form template
        request = self.client.get('/test_admin/admin/admin_views/customarticle/1/')
        self.assertTemplateUsed(request, 'custom_admin/change_form.html')
        request = self.client.get('/test_admin/admin/admin_views/customarticle/1/delete/')
        self.assertTemplateUsed(request, 'custom_admin/delete_confirmation.html')
        request = self.client.get('/test_admin/admin/admin_views/customarticle/1/history/')
        self.assertTemplateUsed(request, 'custom_admin/object_history.html')

        self.client.get('/test_admin/admin/logout/')

    def testDeleteView(self):
        """Delete view should restrict access and actually delete items."""

        delete_dict = {'post': 'yes'}

        # add user shoud not be able to delete articles
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.adduser_login)
        request = self.client.get('/test_admin/admin/admin_views/article/1/delete/')
        self.failUnlessEqual(request.status_code, 403)
        post = self.client.post('/test_admin/admin/admin_views/article/1/delete/', delete_dict)
        self.failUnlessEqual(post.status_code, 403)
        self.failUnlessEqual(Article.objects.all().count(), 3)
        self.client.get('/test_admin/admin/logout/')

        # Delete user can delete
        self.client.get('/test_admin/admin/')
        self.client.post('/test_admin/admin/', self.deleteuser_login)
        response = self.client.get('/test_admin/admin/admin_views/section/1/delete/')
         # test response contains link to related Article
        self.assertContains(response, "admin_views/article/1/")

        response = self.client.get('/test_admin/admin/admin_views/article/1/delete/')
        self.failUnlessEqual(response.status_code, 200)
        post = self.client.post('/test_admin/admin/admin_views/article/1/delete/', delete_dict)
        self.assertRedirects(post, '/test_admin/admin/')
        self.failUnlessEqual(Article.objects.all().count(), 2)
        article_ct = ContentType.objects.get_for_model(Article)
        logged = LogEntry.objects.get(content_type=article_ct, action_flag=DELETION)
        self.failUnlessEqual(logged.object_id, u'1')
        self.client.get('/test_admin/admin/logout/')

    def testDisabledPermissionsWhenLoggedIn(self):
        self.client.login(username='super', password='secret')
        superuser = User.objects.get(username='super')
        superuser.is_active = False
        superuser.save()

        response = self.client.get('/test_admin/admin/')
        self.assertContains(response, 'id="login-form"')
        self.assertNotContains(response, 'Log out')

        response = self.client.get('/test_admin/admin/secure-view/')
        self.assertContains(response, 'id="login-form"')

class AdminViewStringPrimaryKeyTest(TestCase):
    fixtures = ['admin-views-users.xml', 'string-primary-key.xml']

    def __init__(self, *args):
        super(AdminViewStringPrimaryKeyTest, self).__init__(*args)
        self.pk = """abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 1234567890 -_.!~*'() ;/?:@&=+$, <>#%" {}|\^[]`"""

    def setUp(self):
        self.client.login(username='super', password='secret')
        content_type_pk = ContentType.objects.get_for_model(ModelWithStringPrimaryKey).pk
        LogEntry.objects.log_action(100, content_type_pk, self.pk, self.pk, 2, change_message='')

    def tearDown(self):
        self.client.logout()

    def test_get_history_view(self):
        "Retrieving the history for the object using urlencoded form of primary key should work"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/history/' % quote(self.pk))
        self.assertContains(response, escape(self.pk))
        self.failUnlessEqual(response.status_code, 200)

    def test_get_change_view(self):
        "Retrieving the object using urlencoded form of primary key should work"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/' % quote(self.pk))
        self.assertContains(response, escape(self.pk))
        self.failUnlessEqual(response.status_code, 200)

    def test_changelist_to_changeform_link(self):
        "The link from the changelist referring to the changeform of the object should be quoted"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/')
        should_contain = """<th><a href="%s/">%s</a></th></tr>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)

    def test_recentactions_link(self):
        "The link from the recent actions list referring to the changeform of the object should be quoted"
        response = self.client.get('/test_admin/admin/')
        should_contain = """<a href="admin_views/modelwithstringprimarykey/%s/">%s</a>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)

    def test_recentactions_without_content_type(self):
        "If a LogEntry is missing content_type it will not display it in span tag under the hyperlink."
        response = self.client.get('/test_admin/admin/')
        should_contain = """<a href="admin_views/modelwithstringprimarykey/%s/">%s</a>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)
        should_contain = "Model with string primary key" # capitalized in Recent Actions
        self.assertContains(response, should_contain)
        logentry = LogEntry.objects.get(content_type__name__iexact=should_contain)
        # http://code.djangoproject.com/ticket/10275
        # if the log entry doesn't have a content type it should still be
        # possible to view the Recent Actions part
        logentry.content_type = None
        logentry.save()

        counted_presence_before = response.content.count(should_contain)
        response = self.client.get('/test_admin/admin/')
        counted_presence_after = response.content.count(should_contain)
        self.assertEquals(counted_presence_before - 1,
                          counted_presence_after)

    def test_deleteconfirmation_link(self):
        "The link from the delete confirmation page referring back to the changeform of the object should be quoted"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/delete/' % quote(self.pk))
        should_contain = """<a href="../../%s/">%s</a>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)

    def test_url_conflicts_with_add(self):
        "A model with a primary key that ends with add should be visible"
        add_model = ModelWithStringPrimaryKey(id="i have something to add")
        add_model.save()
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/' % quote(add_model.pk))
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)

    def test_url_conflicts_with_delete(self):
        "A model with a primary key that ends with delete should be visible"
        delete_model = ModelWithStringPrimaryKey(id="delete")
        delete_model.save()
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/' % quote(delete_model.pk))
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)

    def test_url_conflicts_with_history(self):
        "A model with a primary key that ends with history should be visible"
        history_model = ModelWithStringPrimaryKey(id="history")
        history_model.save()
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/' % quote(history_model.pk))
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)


class SecureViewTest(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        # login POST dicts
        self.super_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'super',
                     'password': 'secret'}
        self.super_email_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'super@example.com',
                     'password': 'secret'}
        self.super_email_bad_login = {
                      LOGIN_FORM_KEY: 1,
                      'username': 'super@example.com',
                      'password': 'notsecret'}
        self.adduser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'adduser',
                     'password': 'secret'}
        self.changeuser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'changeuser',
                     'password': 'secret'}
        self.deleteuser_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'deleteuser',
                     'password': 'secret'}
        self.joepublic_login = {
                     LOGIN_FORM_KEY: 1,
                     'username': 'joepublic',
                     'password': 'secret'}

    def tearDown(self):
        self.client.logout()

    def test_secure_view_shows_login_if_not_logged_in(self):
        "Ensure that we see the login form"
        response = self.client.get('/test_admin/admin/secure-view/' )
        self.assertTemplateUsed(response, 'admin/login.html')

    def test_secure_view_login_successfully_redirects_to_original_url(self):
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        query_string = "the-answer=42"
        login = self.client.post('/test_admin/admin/secure-view/', self.super_login, QUERY_STRING = query_string )
        self.assertRedirects(login, '/test_admin/admin/secure-view/?%s' % query_string)

    def test_staff_member_required_decorator_works_as_per_admin_login(self):
        """
        Make sure only staff members can log in.

        Successful posts to the login page will redirect to the orignal url.
        Unsuccessfull attempts will continue to render the login page with
        a 200 status code.
        """
        # Super User
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.super_login)
        self.assertRedirects(login, '/test_admin/admin/secure-view/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')
        # make sure the view removes test cookie
        self.failUnlessEqual(self.client.session.test_cookie_worked(), False)

        # Test if user enters e-mail address
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.super_email_login)
        self.assertContains(login, "Your e-mail address is not your username")
        # only correct passwords get a username hint
        login = self.client.post('/test_admin/admin/secure-view/', self.super_email_bad_login)
        self.assertContains(login, "Usernames cannot contain the &#39;@&#39; character")
        new_user = User(username='jondoe', password='secret', email='super@example.com')
        new_user.save()
        # check to ensure if there are multiple e-mail addresses a user doesn't get a 500
        login = self.client.post('/test_admin/admin/secure-view/', self.super_email_login)
        self.assertContains(login, "Usernames cannot contain the &#39;@&#39; character")

        # Add User
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.adduser_login)
        self.assertRedirects(login, '/test_admin/admin/secure-view/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Change User
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.changeuser_login)
        self.assertRedirects(login, '/test_admin/admin/secure-view/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Delete User
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.deleteuser_login)
        self.assertRedirects(login, '/test_admin/admin/secure-view/')
        self.failIf(login.context)
        self.client.get('/test_admin/admin/logout/')

        # Regular User should not be able to login.
        request = self.client.get('/test_admin/admin/secure-view/')
        self.failUnlessEqual(request.status_code, 200)
        login = self.client.post('/test_admin/admin/secure-view/', self.joepublic_login)
        self.failUnlessEqual(login.status_code, 200)
        # Login.context is a list of context dicts we just need to check the first one.
        self.assert_(login.context[0].get('error_message'))

        # 8509 - if a normal user is already logged in, it is possible
        # to change user into the superuser without error
        login = self.client.login(username='joepublic', password='secret')
        # Check and make sure that if user expires, data still persists
        self.client.get('/test_admin/admin/secure-view/')
        self.client.post('/test_admin/admin/secure-view/', self.super_login)
        # make sure the view removes test cookie
        self.failUnlessEqual(self.client.session.test_cookie_worked(), False)

class AdminViewUnicodeTest(TestCase):
    fixtures = ['admin-views-unicode.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testUnicodeEdit(self):
        """
        A test to ensure that POST on edit_view handles non-ascii characters.
        """
        post_data = {
            "name": u"Test lærdommer",
            # inline data
            "chapter_set-TOTAL_FORMS": u"6",
            "chapter_set-INITIAL_FORMS": u"3",
            "chapter_set-0-id": u"1",
            "chapter_set-0-title": u"Norske bostaver æøå skaper problemer",
            "chapter_set-0-content": u"&lt;p&gt;Svært frustrerende med UnicodeDecodeError&lt;/p&gt;",
            "chapter_set-1-id": u"2",
            "chapter_set-1-title": u"Kjærlighet.",
            "chapter_set-1-content": u"&lt;p&gt;La kjærligheten til de lidende seire.&lt;/p&gt;",
            "chapter_set-2-id": u"3",
            "chapter_set-2-title": u"Need a title.",
            "chapter_set-2-content": u"&lt;p&gt;Newest content&lt;/p&gt;",
            "chapter_set-3-id": u"",
            "chapter_set-3-title": u"",
            "chapter_set-3-content": u"",
            "chapter_set-4-id": u"",
            "chapter_set-4-title": u"",
            "chapter_set-4-content": u"",
            "chapter_set-5-id": u"",
            "chapter_set-5-title": u"",
            "chapter_set-5-content": u"",
        }

        response = self.client.post('/test_admin/admin/admin_views/book/1/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

    def testUnicodeDelete(self):
        """
        Ensure that the delete_view handles non-ascii characters
        """
        delete_dict = {'post': 'yes'}
        response = self.client.get('/test_admin/admin/admin_views/book/1/delete/')
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.post('/test_admin/admin/admin_views/book/1/delete/', delete_dict)
        self.assertRedirects(response, '/test_admin/admin/admin_views/book/')


class AdminViewListEditable(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-person.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_inheritance(self):
        Podcast.objects.create(name="This Week in Django",
            release_date=datetime.date.today())
        response = self.client.get('/test_admin/admin/admin_views/podcast/')
        self.failUnlessEqual(response.status_code, 200)

    def test_inheritance_2(self):
        Vodcast.objects.create(name="This Week in Django", released=True)
        response = self.client.get('/test_admin/admin/admin_views/vodcast/')
        self.failUnlessEqual(response.status_code, 200)

    def test_custom_pk(self):
        Language.objects.create(iso='en', name='English', english_name='English')
        response = self.client.get('/test_admin/admin/admin_views/language/')
        self.failUnlessEqual(response.status_code, 200)

    def test_changelist_input_html(self):
        response = self.client.get('/test_admin/admin/admin_views/person/')
        # 2 inputs per object(the field and the hidden id field) = 6
        # 2 management hidden fields = 2
        # 4 action inputs (3 regular checkboxes, 1 checkbox to select all)
        # main form submit button = 1
        # search field and search submit button = 2
        # CSRF field = 1
        # 6 + 2 + 4 + 1 + 2 + 1 = 16 inputs
        self.failUnlessEqual(response.content.count("<input"), 16)
        # 1 select per object = 3 selects
        self.failUnlessEqual(response.content.count("<select"), 4)

    def test_post_submission(self):
        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",

            "form-0-gender": "1",
            "form-0-id": "1",

            "form-1-gender": "2",
            "form-1-id": "2",

            "form-2-alive": "checked",
            "form-2-gender": "1",
            "form-2-id": "3",
        }
        self.client.post('/test_admin/admin/admin_views/person/', data)

        self.failUnlessEqual(Person.objects.get(name="John Mauchly").alive, False)
        self.failUnlessEqual(Person.objects.get(name="Grace Hopper").gender, 2)

        # test a filtered page
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",

            "form-0-id": "1",
            "form-0-gender": "1",
            "form-0-alive": "checked",

            "form-1-id": "3",
            "form-1-gender": "1",
            "form-1-alive": "checked",
        }
        self.client.post('/test_admin/admin/admin_views/person/?gender__exact=1', data)

        self.failUnlessEqual(Person.objects.get(name="John Mauchly").alive, True)

        # test a searched page
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",

            "form-0-id": "1",
            "form-0-gender": "1"
        }
        self.client.post('/test_admin/admin/admin_views/person/?q=mauchly', data)

        self.failUnlessEqual(Person.objects.get(name="John Mauchly").alive, False)

    def test_list_editable_ordering(self):
        collector = Collector.objects.create(id=1, name="Frederick Clegg")

        Category.objects.create(id=1, order=1, collector=collector)
        Category.objects.create(id=2, order=2, collector=collector)
        Category.objects.create(id=3, order=0, collector=collector)
        Category.objects.create(id=4, order=0, collector=collector)

        # NB: The order values must be changed so that the items are reordered.
        data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",

            "form-0-order": "14",
            "form-0-id": "1",
            "form-0-collector": "1",

            "form-1-order": "13",
            "form-1-id": "2",
            "form-1-collector": "1",

            "form-2-order": "1",
            "form-2-id": "3",
            "form-2-collector": "1",

            "form-3-order": "0",
            "form-3-id": "4",
            "form-3-collector": "1",
        }
        response = self.client.post('/test_admin/admin/admin_views/category/', data)
        # Successful post will redirect
        self.failUnlessEqual(response.status_code, 302)

        # Check that the order values have been applied to the right objects
        self.failUnlessEqual(Category.objects.get(id=1).order, 14)
        self.failUnlessEqual(Category.objects.get(id=2).order, 13)
        self.failUnlessEqual(Category.objects.get(id=3).order, 1)
        self.failUnlessEqual(Category.objects.get(id=4).order, 0)

class AdminSearchTest(TestCase):
    fixtures = ['admin-views-users','multiple-child-classes']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_search_on_sibling_models(self):
        "Check that a search that mentions sibling models"
        response = self.client.get('/test_admin/admin/admin_views/recommendation/?q=bar')
        # confirm the search returned 1 object
        self.assertContains(response, "\n1 recommendation\n")

class AdminInheritedInlinesTest(TestCase):
    fixtures = ['admin-views-users.xml',]

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testInline(self):
        "Ensure that inline models which inherit from a common parent are correctly handled by admin."

        foo_user = u"foo username"
        bar_user = u"bar username"

        name_re = re.compile('name="(.*?)"')

        # test the add case
        response = self.client.get('/test_admin/admin/admin_views/persona/add/')
        names = name_re.findall(response.content)
        # make sure we have no duplicate HTML names
        self.failUnlessEqual(len(names), len(set(names)))

        # test the add case
        post_data = {
            "name": u"Test Name",
            # inline data
            "accounts-TOTAL_FORMS": u"1",
            "accounts-INITIAL_FORMS": u"0",
            "accounts-0-username": foo_user,
            "accounts-2-TOTAL_FORMS": u"1",
            "accounts-2-INITIAL_FORMS": u"0",
            "accounts-2-0-username": bar_user,
        }

        response = self.client.post('/test_admin/admin/admin_views/persona/add/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere
        self.failUnlessEqual(Persona.objects.count(), 1)
        self.failUnlessEqual(FooAccount.objects.count(), 1)
        self.failUnlessEqual(BarAccount.objects.count(), 1)
        self.failUnlessEqual(FooAccount.objects.all()[0].username, foo_user)
        self.failUnlessEqual(BarAccount.objects.all()[0].username, bar_user)
        self.failUnlessEqual(Persona.objects.all()[0].accounts.count(), 2)

        # test the edit case

        response = self.client.get('/test_admin/admin/admin_views/persona/1/')
        names = name_re.findall(response.content)
        # make sure we have no duplicate HTML names
        self.failUnlessEqual(len(names), len(set(names)))

        post_data = {
            "name": u"Test Name",

            "accounts-TOTAL_FORMS": "2",
            "accounts-INITIAL_FORMS": u"1",

            "accounts-0-username": "%s-1" % foo_user,
            "accounts-0-account_ptr": "1",
            "accounts-0-persona": "1",

            "accounts-2-TOTAL_FORMS": u"2",
            "accounts-2-INITIAL_FORMS": u"1",

            "accounts-2-0-username": "%s-1" % bar_user,
            "accounts-2-0-account_ptr": "2",
            "accounts-2-0-persona": "1",
        }
        response = self.client.post('/test_admin/admin/admin_views/persona/1/', post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Persona.objects.count(), 1)
        self.failUnlessEqual(FooAccount.objects.count(), 1)
        self.failUnlessEqual(BarAccount.objects.count(), 1)
        self.failUnlessEqual(FooAccount.objects.all()[0].username, "%s-1" % foo_user)
        self.failUnlessEqual(BarAccount.objects.all()[0].username, "%s-1" % bar_user)
        self.failUnlessEqual(Persona.objects.all()[0].accounts.count(), 2)

from django.core import mail

class AdminActionsTest(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-actions.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_model_admin_custom_action(self):
        "Tests a custom action defined in a ModelAdmin method"
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            'action' : 'mail_admin',
            'index': 0,
        }
        response = self.client.post('/test_admin/admin/admin_views/subscriber/', action_data)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, 'Greetings from a ModelAdmin action')

    def test_model_admin_default_delete_action(self):
        "Tests the default delete action defined as a ModelAdmin method"
        action_data = {
            ACTION_CHECKBOX_NAME: [1, 2],
            'action' : 'delete_selected',
            'index': 0,
        }
        delete_confirmation_data = {
            ACTION_CHECKBOX_NAME: [1, 2],
            'action' : 'delete_selected',
            'index': 0,
            'post': 'yes',
        }
        confirmation = self.client.post('/test_admin/admin/admin_views/subscriber/', action_data)
        self.assertContains(confirmation, "Are you sure you want to delete the selected subscriber objects")
        self.failUnless(confirmation.content.count(ACTION_CHECKBOX_NAME) == 2)
        response = self.client.post('/test_admin/admin/admin_views/subscriber/', delete_confirmation_data)
        self.failUnlessEqual(Subscriber.objects.count(), 0)

    def test_custom_function_mail_action(self):
        "Tests a custom action defined in a function"
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            'action' : 'external_mail',
            'index': 0,
        }
        response = self.client.post('/test_admin/admin/admin_views/externalsubscriber/', action_data)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, 'Greetings from a function action')

    def test_custom_function_action_with_redirect(self):
        "Tests a custom action defined in a function"
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            'action' : 'redirect_to',
            'index': 0,
        }
        response = self.client.post('/test_admin/admin/admin_views/externalsubscriber/', action_data)
        self.failUnlessEqual(response.status_code, 302)

    def test_model_without_action(self):
        "Tests a ModelAdmin without any action"
        response = self.client.get('/test_admin/admin/admin_views/oldsubscriber/')
        self.assertEquals(response.context["action_form"], None)
        self.assert_(
            '<input type="checkbox" class="action-select"' not in response.content,
            "Found an unexpected action toggle checkboxbox in response"
        )
        self.assert_('action-checkbox-column' not in response.content,
            "Found unexpected action-checkbox-column class in response")

    def test_action_column_class(self):
        "Tests that the checkbox column class is present in the response"
        response = self.client.get('/test_admin/admin/admin_views/subscriber/')
        self.assertNotEquals(response.context["action_form"], None)
        self.assert_('action-checkbox-column' in response.content,
            "Expected an action-checkbox-column in response")

    def test_multiple_actions_form(self):
        """
        Test that actions come from the form whose submit button was pressed (#10618).
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            # Two different actions selected on the two forms...
            'action': ['external_mail', 'delete_selected'],
            # ...but we clicked "go" on the top form.
            'index': 0
        }
        response = self.client.post('/test_admin/admin/admin_views/externalsubscriber/', action_data)

        # Send mail, don't delete.
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, 'Greetings from a function action')

    def test_user_message_on_none_selected(self):
        """
        User should see a warning when 'Go' is pressed and no items are selected.
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [],
            'action' : 'delete_selected',
            'index': 0,
        }
        response = self.client.post('/test_admin/admin/admin_views/subscriber/', action_data)
        msg = """Items must be selected in order to perform actions on them. No items have been changed."""
        self.assertContains(response, msg)
        self.failUnlessEqual(Subscriber.objects.count(), 2)

    def test_user_message_on_no_action(self):
        """
        User should see a warning when 'Go' is pressed and no action is selected.
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [1, 2],
            'action' : '',
            'index': 0,
        }
        response = self.client.post('/test_admin/admin/admin_views/subscriber/', action_data)
        msg = """No action selected."""
        self.assertContains(response, msg)
        self.failUnlessEqual(Subscriber.objects.count(), 2)

    def test_selection_counter(self):
        """
        Check if the selection counter is there.
        """
        response = self.client.get('/test_admin/admin/admin_views/subscriber/')
        self.assertContains(response, '<span class="_acnt">0</span> of 2 subscribers selected')


class TestCustomChangeList(TestCase):
    fixtures = ['admin-views-users.xml']
    urlbit = 'admin'

    def setUp(self):
        result = self.client.login(username='super', password='secret')
        self.failUnlessEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test_custom_changelist(self):
        """
        Validate that a custom ChangeList class can be used (#9749)
        """
        # Insert some data
        post_data = {"name": u"First Gadget"}
        response = self.client.post('/test_admin/%s/admin_views/gadget/add/' % self.urlbit, post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere
        # Hit the page once to get messages out of the queue message list
        response = self.client.get('/test_admin/%s/admin_views/gadget/' % self.urlbit)
        # Ensure that that data is still not visible on the page
        response = self.client.get('/test_admin/%s/admin_views/gadget/' % self.urlbit)
        self.failUnlessEqual(response.status_code, 200)
        self.assertNotContains(response, 'First Gadget')


class TestInlineNotEditable(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        result = self.client.login(username='super', password='secret')
        self.failUnlessEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test(self):
        """
        InlineModelAdmin broken?
        """
        response = self.client.get('/test_admin/admin/admin_views/parent/add/')
        self.failUnlessEqual(response.status_code, 200)

class AdminCustomQuerysetTest(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')
        self.pks = [EmptyModel.objects.create().id for i in range(3)]

    def test_changelist_view(self):
        response = self.client.get('/test_admin/admin/admin_views/emptymodel/')
        for i in self.pks:
            if i > 1:
                self.assertContains(response, 'Primary key = %s' % i)
            else:
                self.assertNotContains(response, 'Primary key = %s' % i)

    def test_change_view(self):
        for i in self.pks:
            response = self.client.get('/test_admin/admin/admin_views/emptymodel/%s/' % i)
            if i > 1:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

class AdminInlineFileUploadTest(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-actions.xml']
    urlbit = 'admin'

    def setUp(self):
        self.client.login(username='super', password='secret')

        # Set up test Picture and Gallery.
        # These must be set up here instead of in fixtures in order to allow Picture
        # to use a NamedTemporaryFile.
        tdir = tempfile.gettempdir()
        file1 = tempfile.NamedTemporaryFile(suffix=".file1", dir=tdir)
        file1.write('a' * (2 ** 21))
        filename = file1.name
        file1.close()
        g = Gallery(name="Test Gallery")
        g.save()
        p = Picture(name="Test Picture", image=filename, gallery=g)
        p.save()

    def tearDown(self):
        self.client.logout()

    def test_inline_file_upload_edit_validation_error_post(self):
        """
        Test that inline file uploads correctly display prior data (#10002).
        """
        post_data = {
            "name": u"Test Gallery",
            "pictures-TOTAL_FORMS": u"2",
            "pictures-INITIAL_FORMS": u"1",
            "pictures-0-id": u"1",
            "pictures-0-gallery": u"1",
            "pictures-0-name": "Test Picture",
            "pictures-0-image": "",
            "pictures-1-id": "",
            "pictures-1-gallery": "1",
            "pictures-1-name": "Test Picture 2",
            "pictures-1-image": "",
        }
        response = self.client.post('/test_admin/%s/admin_views/gallery/1/' % self.urlbit, post_data)
        self.failUnless(response._container[0].find("Currently:") > -1)


class AdminInlineTests(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        self.post_data = {
            "name": u"Test Name",

            "widget_set-TOTAL_FORMS": "3",
            "widget_set-INITIAL_FORMS": u"0",
            "widget_set-0-id": "",
            "widget_set-0-owner": "1",
            "widget_set-0-name": "",
            "widget_set-1-id": "",
            "widget_set-1-owner": "1",
            "widget_set-1-name": "",
            "widget_set-2-id": "",
            "widget_set-2-owner": "1",
            "widget_set-2-name": "",

            "doohickey_set-TOTAL_FORMS": "3",
            "doohickey_set-INITIAL_FORMS": u"0",
            "doohickey_set-0-owner": "1",
            "doohickey_set-0-code": "",
            "doohickey_set-0-name": "",
            "doohickey_set-1-owner": "1",
            "doohickey_set-1-code": "",
            "doohickey_set-1-name": "",
            "doohickey_set-2-owner": "1",
            "doohickey_set-2-code": "",
            "doohickey_set-2-name": "",

            "grommet_set-TOTAL_FORMS": "3",
            "grommet_set-INITIAL_FORMS": u"0",
            "grommet_set-0-code": "",
            "grommet_set-0-owner": "1",
            "grommet_set-0-name": "",
            "grommet_set-1-code": "",
            "grommet_set-1-owner": "1",
            "grommet_set-1-name": "",
            "grommet_set-2-code": "",
            "grommet_set-2-owner": "1",
            "grommet_set-2-name": "",

            "whatsit_set-TOTAL_FORMS": "3",
            "whatsit_set-INITIAL_FORMS": u"0",
            "whatsit_set-0-owner": "1",
            "whatsit_set-0-index": "",
            "whatsit_set-0-name": "",
            "whatsit_set-1-owner": "1",
            "whatsit_set-1-index": "",
            "whatsit_set-1-name": "",
            "whatsit_set-2-owner": "1",
            "whatsit_set-2-index": "",
            "whatsit_set-2-name": "",

            "fancydoodad_set-TOTAL_FORMS": "3",
            "fancydoodad_set-INITIAL_FORMS": u"0",
            "fancydoodad_set-0-doodad_ptr": "",
            "fancydoodad_set-0-owner": "1",
            "fancydoodad_set-0-name": "",
            "fancydoodad_set-0-expensive": "on",
            "fancydoodad_set-1-doodad_ptr": "",
            "fancydoodad_set-1-owner": "1",
            "fancydoodad_set-1-name": "",
            "fancydoodad_set-1-expensive": "on",
            "fancydoodad_set-2-doodad_ptr": "",
            "fancydoodad_set-2-owner": "1",
            "fancydoodad_set-2-name": "",
            "fancydoodad_set-2-expensive": "on",

            "category_set-TOTAL_FORMS": "3",
            "category_set-INITIAL_FORMS": "0",
            "category_set-0-order": "",
            "category_set-0-id": "",
            "category_set-0-collector": "1",
            "category_set-1-order": "",
            "category_set-1-id": "",
            "category_set-1-collector": "1",
            "category_set-2-order": "",
            "category_set-2-id": "",
            "category_set-2-collector": "1",
        }

        result = self.client.login(username='super', password='secret')
        self.failUnlessEqual(result, True)
        self.collector = Collector(pk=1,name='John Fowles')
        self.collector.save()

    def tearDown(self):
        self.client.logout()

    def test_simple_inline(self):
        "A simple model can be saved as inlines"
        # First add a new inline
        self.post_data['widget_set-0-name'] = "Widget 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Widget.objects.count(), 1)
        self.failUnlessEqual(Widget.objects.all()[0].name, "Widget 1")

        # Check that the PK link exists on the rendered form
        response = self.client.get('/test_admin/admin/admin_views/collector/1/')
        self.assertContains(response, 'name="widget_set-0-id"')

        # Now resave that inline
        self.post_data['widget_set-INITIAL_FORMS'] = "1"
        self.post_data['widget_set-0-id'] = "1"
        self.post_data['widget_set-0-name'] = "Widget 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Widget.objects.count(), 1)
        self.failUnlessEqual(Widget.objects.all()[0].name, "Widget 1")

        # Now modify that inline
        self.post_data['widget_set-INITIAL_FORMS'] = "1"
        self.post_data['widget_set-0-id'] = "1"
        self.post_data['widget_set-0-name'] = "Widget 1 Updated"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Widget.objects.count(), 1)
        self.failUnlessEqual(Widget.objects.all()[0].name, "Widget 1 Updated")

    def test_explicit_autofield_inline(self):
        "A model with an explicit autofield primary key can be saved as inlines. Regression for #8093"
        # First add a new inline
        self.post_data['grommet_set-0-name'] = "Grommet 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Grommet.objects.count(), 1)
        self.failUnlessEqual(Grommet.objects.all()[0].name, "Grommet 1")

        # Check that the PK link exists on the rendered form
        response = self.client.get('/test_admin/admin/admin_views/collector/1/')
        self.assertContains(response, 'name="grommet_set-0-code"')

        # Now resave that inline
        self.post_data['grommet_set-INITIAL_FORMS'] = "1"
        self.post_data['grommet_set-0-code'] = "1"
        self.post_data['grommet_set-0-name'] = "Grommet 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Grommet.objects.count(), 1)
        self.failUnlessEqual(Grommet.objects.all()[0].name, "Grommet 1")

        # Now modify that inline
        self.post_data['grommet_set-INITIAL_FORMS'] = "1"
        self.post_data['grommet_set-0-code'] = "1"
        self.post_data['grommet_set-0-name'] = "Grommet 1 Updated"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Grommet.objects.count(), 1)
        self.failUnlessEqual(Grommet.objects.all()[0].name, "Grommet 1 Updated")

    def test_char_pk_inline(self):
        "A model with a character PK can be saved as inlines. Regression for #10992"
        # First add a new inline
        self.post_data['doohickey_set-0-code'] = "DH1"
        self.post_data['doohickey_set-0-name'] = "Doohickey 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(DooHickey.objects.count(), 1)
        self.failUnlessEqual(DooHickey.objects.all()[0].name, "Doohickey 1")

        # Check that the PK link exists on the rendered form
        response = self.client.get('/test_admin/admin/admin_views/collector/1/')
        self.assertContains(response, 'name="doohickey_set-0-code"')

        # Now resave that inline
        self.post_data['doohickey_set-INITIAL_FORMS'] = "1"
        self.post_data['doohickey_set-0-code'] = "DH1"
        self.post_data['doohickey_set-0-name'] = "Doohickey 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(DooHickey.objects.count(), 1)
        self.failUnlessEqual(DooHickey.objects.all()[0].name, "Doohickey 1")

        # Now modify that inline
        self.post_data['doohickey_set-INITIAL_FORMS'] = "1"
        self.post_data['doohickey_set-0-code'] = "DH1"
        self.post_data['doohickey_set-0-name'] = "Doohickey 1 Updated"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(DooHickey.objects.count(), 1)
        self.failUnlessEqual(DooHickey.objects.all()[0].name, "Doohickey 1 Updated")

    def test_integer_pk_inline(self):
        "A model with an integer PK can be saved as inlines. Regression for #10992"
        # First add a new inline
        self.post_data['whatsit_set-0-index'] = "42"
        self.post_data['whatsit_set-0-name'] = "Whatsit 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Whatsit.objects.count(), 1)
        self.failUnlessEqual(Whatsit.objects.all()[0].name, "Whatsit 1")

        # Check that the PK link exists on the rendered form
        response = self.client.get('/test_admin/admin/admin_views/collector/1/')
        self.assertContains(response, 'name="whatsit_set-0-index"')

        # Now resave that inline
        self.post_data['whatsit_set-INITIAL_FORMS'] = "1"
        self.post_data['whatsit_set-0-index'] = "42"
        self.post_data['whatsit_set-0-name'] = "Whatsit 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Whatsit.objects.count(), 1)
        self.failUnlessEqual(Whatsit.objects.all()[0].name, "Whatsit 1")

        # Now modify that inline
        self.post_data['whatsit_set-INITIAL_FORMS'] = "1"
        self.post_data['whatsit_set-0-index'] = "42"
        self.post_data['whatsit_set-0-name'] = "Whatsit 1 Updated"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(Whatsit.objects.count(), 1)
        self.failUnlessEqual(Whatsit.objects.all()[0].name, "Whatsit 1 Updated")

    def test_inherited_inline(self):
        "An inherited model can be saved as inlines. Regression for #11042"
        # First add a new inline
        self.post_data['fancydoodad_set-0-name'] = "Fancy Doodad 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(FancyDoodad.objects.count(), 1)
        self.failUnlessEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1")

        # Check that the PK link exists on the rendered form
        response = self.client.get('/test_admin/admin/admin_views/collector/1/')
        self.assertContains(response, 'name="fancydoodad_set-0-doodad_ptr"')

        # Now resave that inline
        self.post_data['fancydoodad_set-INITIAL_FORMS'] = "1"
        self.post_data['fancydoodad_set-0-doodad_ptr'] = "1"
        self.post_data['fancydoodad_set-0-name'] = "Fancy Doodad 1"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(FancyDoodad.objects.count(), 1)
        self.failUnlessEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1")

        # Now modify that inline
        self.post_data['fancydoodad_set-INITIAL_FORMS'] = "1"
        self.post_data['fancydoodad_set-0-doodad_ptr'] = "1"
        self.post_data['fancydoodad_set-0-name'] = "Fancy Doodad 1 Updated"
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(FancyDoodad.objects.count(), 1)
        self.failUnlessEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1 Updated")

    def test_ordered_inline(self):
        """Check that an inline with an editable ordering fields is
        updated correctly. Regression for #10922"""
        # Create some objects with an initial ordering
        Category.objects.create(id=1, order=1, collector=self.collector)
        Category.objects.create(id=2, order=2, collector=self.collector)
        Category.objects.create(id=3, order=0, collector=self.collector)
        Category.objects.create(id=4, order=0, collector=self.collector)

        # NB: The order values must be changed so that the items are reordered.
        self.post_data.update({
            "name": "Frederick Clegg",

            "category_set-TOTAL_FORMS": "7",
            "category_set-INITIAL_FORMS": "4",

            "category_set-0-order": "14",
            "category_set-0-id": "1",
            "category_set-0-collector": "1",

            "category_set-1-order": "13",
            "category_set-1-id": "2",
            "category_set-1-collector": "1",

            "category_set-2-order": "1",
            "category_set-2-id": "3",
            "category_set-2-collector": "1",

            "category_set-3-order": "0",
            "category_set-3-id": "4",
            "category_set-3-collector": "1",

            "category_set-4-order": "",
            "category_set-4-id": "",
            "category_set-4-collector": "1",

            "category_set-5-order": "",
            "category_set-5-id": "",
            "category_set-5-collector": "1",

            "category_set-6-order": "",
            "category_set-6-id": "",
            "category_set-6-collector": "1",
        })
        response = self.client.post('/test_admin/admin/admin_views/collector/1/', self.post_data)
        # Successful post will redirect
        self.failUnlessEqual(response.status_code, 302)

        # Check that the order values have been applied to the right objects
        self.failUnlessEqual(self.collector.category_set.count(), 4)
        self.failUnlessEqual(Category.objects.get(id=1).order, 14)
        self.failUnlessEqual(Category.objects.get(id=2).order, 13)
        self.failUnlessEqual(Category.objects.get(id=3).order, 1)
        self.failUnlessEqual(Category.objects.get(id=4).order, 0)


class NeverCacheTests(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-colors.xml', 'admin-views-fabrics.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testAdminIndex(self):
        "Check the never-cache status of the main index"
        response = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testAppIndex(self):
        "Check the never-cache status of an application index"
        response = self.client.get('/test_admin/admin/admin_views/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testModelIndex(self):
        "Check the never-cache status of a model index"
        response = self.client.get('/test_admin/admin/admin_views/fabric/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testModelAdd(self):
        "Check the never-cache status of a model add page"
        response = self.client.get('/test_admin/admin/admin_views/fabric/add/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testModelView(self):
        "Check the never-cache status of a model edit page"
        response = self.client.get('/test_admin/admin/admin_views/section/1/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testModelHistory(self):
        "Check the never-cache status of a model history page"
        response = self.client.get('/test_admin/admin/admin_views/section/1/history/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testModelDelete(self):
        "Check the never-cache status of a model delete page"
        response = self.client.get('/test_admin/admin/admin_views/section/1/delete/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testLogin(self):
        "Check the never-cache status of login views"
        self.client.logout()
        response = self.client.get('/test_admin/admin/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testLogout(self):
        "Check the never-cache status of logout view"
        response = self.client.get('/test_admin/admin/logout/')
        self.failUnlessEqual(get_max_age(response), 0)

    def testPasswordChange(self):
        "Check the never-cache status of the password change view"
        self.client.logout()
        response = self.client.get('/test_admin/password_change/')
        self.failUnlessEqual(get_max_age(response), None)

    def testPasswordChangeDone(self):
        "Check the never-cache status of the password change done view"
        response = self.client.get('/test_admin/admin/password_change/done/')
        self.failUnlessEqual(get_max_age(response), None)

    def testJsi18n(self):
        "Check the never-cache status of the Javascript i18n view"
        response = self.client.get('/test_admin/jsi18n/')
        self.failUnlessEqual(get_max_age(response), None)


class ReadonlyTest(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_readonly_get(self):
        response = self.client.get('/test_admin/admin/admin_views/post/add/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="posted"')
        # 3 fields + 2 submit buttons + 2 inline management form fields, + 2
        # hidden fields for inlines + 1 field for the inline
        self.assertEqual(response.content.count("input"), 10)
        self.assertContains(response, formats.localize(datetime.date.today()))
        self.assertContains(response,
            "<label>Awesomeness level:</label>")
        self.assertContains(response, "Very awesome.")
        self.assertContains(response, "Unkown coolness.")
        self.assertContains(response, "foo")
        self.assertContains(response,
            formats.localize(datetime.date.today() - datetime.timedelta(days=7))
        )

        p = Post.objects.create(title="I worked on readonly_fields", content="Its good stuff")
        response = self.client.get('/test_admin/admin/admin_views/post/%d/' % p.pk)
        self.assertContains(response, "%d amount of cool" % p.pk)

    def test_readonly_post(self):
        data = {
            "title": "Django Got Readonly Fields",
            "content": "This is an incredible development.",
            "link_set-TOTAL_FORMS": "1",
            "link_set-INITIAL_FORMS": "0",
        }
        response = self.client.post('/test_admin/admin/admin_views/post/add/', data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)
        p = Post.objects.get()
        self.assertEqual(p.posted, datetime.date.today())

        data["posted"] = "10-8-1990" # some date that's not today
        response = self.client.post('/test_admin/admin/admin_views/post/add/', data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 2)
        p = Post.objects.order_by('-id')[0]
        self.assertEqual(p.posted, datetime.date.today())

class IncompleteFormTest(TestCase):
    """
    Tests validation of a ModelForm that doesn't explicitly have all data
    corresponding to model fields. Model validation shouldn't fail
    such a forms.
    """
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_user_creation(self):
        response = self.client.post('/test_admin/admin/auth/user/add/', {
            'username': 'newuser',
            'password1': 'newpassword',
            'password2': 'newpassword',
            '_continue': '1',
        })
        new_user = User.objects.order_by('-id')[0]
        self.assertRedirects(response, '/test_admin/admin/auth/user/%s/' % new_user.pk)
        self.assertNotEquals(new_user.password, UNUSABLE_PASSWORD)

    def test_password_mismatch(self):
        response = self.client.post('/test_admin/admin/auth/user/add/', {
            'username': 'newuser',
            'password1': 'newpassword',
            'password2': 'mismatch',
        })
        self.assertEquals(response.status_code, 200)
        adminform = response.context['adminform']
        self.assert_('password' not in adminform.form.errors)
        self.assertEquals(adminform.form.errors['password2'],
                          [u"The two password fields didn't match."])
