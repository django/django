import datetime

from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from regressiontests.views.models import Article, UrlArticle

class CreateObjectTest(TestCase):

    fixtures = ['testdata.json']

    def test_login_required_view(self):
        """
        Verifies that an unauthenticated user attempting to access a
        login_required view gets redirected to the login page and that
        an authenticated user is let through.
        """
        view_url = '/views/create_update/member/create/article/'
        response = self.client.get(view_url)
        self.assertRedirects(response, '/accounts/login/?next=%s' % view_url)
        # Now login and try again.
        login = self.client.login(username='testclient', password='password')
        self.failUnless(login, 'Could not log in')
        response = self.client.get(view_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'views/article_form.html')

    def test_create_article_display_page(self):
        """
        Ensures the generic view returned the page and contains a form.
        """
        view_url = '/views/create_update/create/article/'
        response = self.client.get(view_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'views/article_form.html')
        if not response.context.get('form'):
            self.fail('No form found in the response.')

    def test_create_article_with_errors(self):
        """
        POSTs a form that contains validation errors.
        """
        view_url = '/views/create_update/create/article/'
        num_articles = Article.objects.count()
        response = self.client.post(view_url, {
            'title': 'My First Article',
        })
        self.assertFormError(response, 'form', 'slug', [u'This field is required.'])
        self.assertTemplateUsed(response, 'views/article_form.html')
        self.assertEqual(num_articles, Article.objects.count(),
                         "Number of Articles should not have changed.")

    def test_create_custom_save_article(self):
        """
        Creates a new article using a custom form class with a save method
        that alters the slug entered.
        """
        view_url = '/views/create_update/create_custom/article/'
        response = self.client.post(view_url, {
            'title': 'Test Article',
            'slug': 'this-should-get-replaced',
            'author': 1,
            'date_created': datetime.datetime(2007, 6, 25),
        })
        self.assertRedirects(response,
            '/views/create_update/view/article/some-other-slug/',
            target_status_code=404)

class UpdateDeleteObjectTest(TestCase):

    fixtures = ['testdata.json']

    def test_update_object_form_display(self):
        """
        Verifies that the form was created properly and with initial values.
        """
        response = self.client.get('/views/create_update/update/article/old_article/')
        self.assertTemplateUsed(response, 'views/article_form.html')
        self.assertEquals(unicode(response.context['form']['title']),
            u'<input id="id_title" type="text" name="title" value="Old Article" maxlength="100" />')

    def test_update_object(self):
        """
        Verifies the updating of an Article.
        """
        response = self.client.post('/views/create_update/update/article/old_article/', {
            'title': 'Another Article',
            'slug': 'another-article-slug',
            'author': 1,
            'date_created': datetime.datetime(2007, 6, 25),
        })
        article = Article.objects.get(pk=1)
        self.assertEquals(article.title, "Another Article")

    def test_delete_object_confirm(self):
        """
        Verifies the confirm deletion page is displayed using a GET.
        """
        response = self.client.get('/views/create_update/delete/article/old_article/')
        self.assertTemplateUsed(response, 'views/article_confirm_delete.html')

    def test_delete_object(self):
        """
        Verifies the object actually gets deleted on a POST.
        """
        view_url = '/views/create_update/delete/article/old_article/'
        response = self.client.post(view_url)
        try:
            Article.objects.get(slug='old_article')
        except Article.DoesNotExist:
            pass
        else:
            self.fail('Object was not deleted.')

class PostSaveRedirectTests(TestCase):
    """
    Verifies that the views redirect to the correct locations depending on
    if a post_save_redirect was passed and a get_absolute_url method exists
    on the Model.
    """

    fixtures = ['testdata.json']
    article_model = Article

    create_url = '/views/create_update/create/article/'
    update_url = '/views/create_update/update/article/old_article/'
    delete_url = '/views/create_update/delete/article/old_article/'

    create_redirect = '/views/create_update/view/article/my-first-article/'
    update_redirect = '/views/create_update/view/article/another-article-slug/'
    delete_redirect = '/views/create_update/'

    def test_create_article(self):
        num_articles = self.article_model.objects.count()
        response = self.client.post(self.create_url, {
            'title': 'My First Article',
            'slug': 'my-first-article',
            'author': '1',
            'date_created': datetime.datetime(2007, 6, 25),
        })
        self.assertRedirects(response, self.create_redirect,
                             target_status_code=404)
        self.assertEqual(num_articles + 1, self.article_model.objects.count(),
                         "A new Article should have been created.")

    def test_update_article(self):
        num_articles = self.article_model.objects.count()
        response = self.client.post(self.update_url, {
            'title': 'Another Article',
            'slug': 'another-article-slug',
            'author': 1,
            'date_created': datetime.datetime(2007, 6, 25),
        })
        self.assertRedirects(response, self.update_redirect,
                             target_status_code=404)
        self.assertEqual(num_articles, self.article_model.objects.count(),
                         "A new Article should not have been created.")

    def test_delete_article(self):
        num_articles = self.article_model.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.delete_redirect,
                             target_status_code=404)
        self.assertEqual(num_articles - 1, self.article_model.objects.count(),
                         "An Article should have been deleted.")

class NoPostSaveNoAbsoluteUrl(PostSaveRedirectTests):
    """
    Tests that when no post_save_redirect is passed and no get_absolute_url
    method exists on the Model that the view raises an ImproperlyConfigured
    error.
    """

    create_url = '/views/create_update/no_redirect/create/article/'
    update_url = '/views/create_update/no_redirect/update/article/old_article/'

    def test_create_article(self):
        self.assertRaises(ImproperlyConfigured,
            super(NoPostSaveNoAbsoluteUrl, self).test_create_article)

    def test_update_article(self):
        self.assertRaises(ImproperlyConfigured,
            super(NoPostSaveNoAbsoluteUrl, self).test_update_article)

    def test_delete_article(self):
        """
        The delete_object view requires a post_delete_redirect, so skip testing
        here.
        """
        pass

class AbsoluteUrlNoPostSave(PostSaveRedirectTests):
    """
    Tests that the views redirect to the Model's get_absolute_url when no
    post_save_redirect is passed.
    """

    # Article model with get_absolute_url method.
    article_model = UrlArticle

    create_url = '/views/create_update/no_url/create/article/'
    update_url = '/views/create_update/no_url/update/article/old_article/'

    create_redirect = '/urlarticles/my-first-article/'
    update_redirect = '/urlarticles/another-article-slug/'

    def test_delete_article(self):
        """
        The delete_object view requires a post_delete_redirect, so skip testing
        here.
        """
        pass
