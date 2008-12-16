# coding: utf-8

from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import LOGIN_FORM_KEY
from django.contrib.admin.util import quote
from django.utils.html import escape

# local test models
from models import Article, CustomArticle, Section, ModelWithStringPrimaryKey

class AdminViewBasicTest(TestCase):
    fixtures = ['admin-views-users.xml', 'admin-views-colors.xml']
    
    def setUp(self):
        self.client.login(username='super', password='secret')
    
    def tearDown(self):
        self.client.logout()
    
    def testTrailingSlashRequired(self):
        """
        If you leave off the trailing slash, app should redirect and add it.
        """
        request = self.client.get('/test_admin/admin/admin_views/article/add')
        self.assertRedirects(request,
            '/test_admin/admin/admin_views/article/add/'
        )
    
    def testBasicAddGet(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get('/test_admin/admin/admin_views/section/add/')
        self.failUnlessEqual(response.status_code, 200)
    
    def testAddWithGETArgs(self):
        response = self.client.get('/test_admin/admin/admin_views/section/add/', {'name': 'My Section'})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            'value="My Section"' in response.content, 
            "Couldn't find an input with the right value in the response."
        )
    
    def testBasicEditGet(self):
        """
        A smoke test to ensureGET on the change_view works.
        """
        response = self.client.get('/test_admin/admin/admin_views/section/1/')
        self.failUnlessEqual(response.status_code, 200)
    
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
        response = self.client.post('/test_admin/admin/admin_views/section/add/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere
    
    def testBasicEditPost(self):
        """
        A smoke test to ensure POST on edit_view works.
        """
        post_data = {
            "name": u"Test section",
            # inline data
            "article_set-TOTAL_FORMS": u"6",
            "article_set-INITIAL_FORMS": u"3",
            "article_set-0-id": u"1",
            # there is no title in database, give one here or formset
            # will fail.
            "article_set-0-title": u"Norske bostaver æøå skaper problemer",
            "article_set-0-content": u"&lt;p&gt;Middle content&lt;/p&gt;",
            "article_set-0-date_0": u"2008-03-18",
            "article_set-0-date_1": u"11:54:58",
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
        response = self.client.post('/test_admin/admin/admin_views/section/1/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

    def testChangeListSortingCallable(self):
        """
        Ensure we can sort on a list_display field that is a callable 
        (column 2 is callable_year in ArticleAdmin)
        """
        response = self.client.get('/test_admin/admin/admin_views/article/', {'ot': 'asc', 'o': 2})
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
        response = self.client.get('/test_admin/admin/admin_views/article/', {'ot': 'dsc', 'o': 3})
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
        response = self.client.get('/test_admin/admin/admin_views/article/', {'ot': 'asc', 'o': 4})
        self.failUnlessEqual(response.status_code, 200)
        self.failUnless(
            response.content.index('Oldest content') < response.content.index('Middle content') and 
            response.content.index('Middle content') < response.content.index('Newest content'),
            "Results of sorting on ModelAdmin method are out of order."
        )
        
    def testLimitedFilter(self):
        """Ensure admin changelist filters do not contain objects excluded via limit_choices_to."""
        response = self.client.get('/test_admin/admin/admin_views/thing/')
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
        response = self.client.get('/test_admin/admin/admin_views/thing/', {'notarealfield': '5'})
        self.assertRedirects(response, '/test_admin/admin/admin_views/thing/?e=1')        
        response = self.client.get('/test_admin/admin/admin_views/thing/', {'color__id__exact': 'StringNotInteger!'})
        self.assertRedirects(response, '/test_admin/admin/admin_views/thing/?e=1')
            
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

        # Test custom change form template
        request = self.client.get('/test_admin/admin/admin_views/customarticle/add/')
        self.assertTemplateUsed(request, 'custom_admin/change_form.html')

        # Add an article so we can test delete and history views
        post = self.client.post('/test_admin/admin/admin_views/customarticle/add/', {
            'content': '<p>great article</p>',
            'date_0': '2008-03-18',
            'date_1': '10:54:39'
        })
        self.assertRedirects(post, '/test_admin/admin/admin_views/customarticle/')
        self.failUnlessEqual(CustomArticle.objects.all().count(), 1)

        # Test custom delete and object history templates
        request = self.client.get('/test_admin/admin/admin_views/customarticle/1/delete/')
        self.assertTemplateUsed(request, 'custom_admin/delete_confirmation.html')
        request = self.client.get('/test_admin/admin/admin_views/customarticle/1/history/')
        self.assertTemplateUsed(request, 'custom_admin/object_history.html')

        self.client.get('/test_admin/admin/logout/')

    def testCustomAdminSiteTemplates(self):
        from django.contrib import admin
        self.assertEqual(admin.site.index_template, None)
        self.assertEqual(admin.site.login_template, None)

        self.client.get('/test_admin/admin/logout/')
        request = self.client.get('/test_admin/admin/')
        self.assertTemplateUsed(request, 'admin/login.html')
        self.client.post('/test_admin/admin/', self.changeuser_login)
        request = self.client.get('/test_admin/admin/')
        self.assertTemplateUsed(request, 'admin/index.html')

        self.client.get('/test_admin/admin/logout/')
        admin.site.login_template = 'custom_admin/login.html'
        admin.site.index_template = 'custom_admin/index.html'
        request = self.client.get('/test_admin/admin/')
        self.assertTemplateUsed(request, 'custom_admin/login.html')
        self.assert_('Hello from a custom login template' in request.content)
        self.client.post('/test_admin/admin/', self.changeuser_login)
        request = self.client.get('/test_admin/admin/')
        self.assertTemplateUsed(request, 'custom_admin/index.html')
        self.assert_('Hello from a custom index template' in request.content)

        # Finally, using monkey patching check we can inject custom_context arguments in to index
        original_index = admin.site.index
        def index(*args, **kwargs):
            kwargs['extra_context'] = {'foo': '*bar*'}
            return original_index(*args, **kwargs)
        admin.site.index = index
        request = self.client.get('/test_admin/admin/')
        self.assertTemplateUsed(request, 'custom_admin/index.html')
        self.assert_('Hello from a custom index template *bar*' in request.content)

        self.client.get('/test_admin/admin/logout/')
        del admin.site.index # Resets to using the original
        admin.site.login_template = None
        admin.site.index_template = None

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
        self.client.get('/test_admin/admin/logout/')

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

    def test_get_change_view(self):
        "Retrieving the object using urlencoded form of primary key should work"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/%s/' % quote(self.pk))
        self.assertContains(response, escape(self.pk))
        self.failUnlessEqual(response.status_code, 200)

    def test_changelist_to_changeform_link(self):
        "The link from the changelist referring to the changeform of the object should be quoted"
        response = self.client.get('/test_admin/admin/admin_views/modelwithstringprimarykey/')
        should_contain = """<tr class="row1"><th><a href="%s/">%s</a></th></tr>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)

    def test_recentactions_link(self):
        "The link from the recent actions list referring to the changeform of the object should be quoted"
        response = self.client.get('/test_admin/admin/')
        should_contain = """<a href="admin_views/modelwithstringprimarykey/%s/">%s</a>""" % (quote(self.pk), escape(self.pk))
        self.assertContains(response, should_contain)

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
