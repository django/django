# Django Test Assertions

Complete reference for all Django test assertions with examples.

## Table of Contents

- [Response Assertions](#response-assertions)
- [Template Assertions](#template-assertions)
- [Form Assertions](#form-assertions)
- [Database Assertions](#database-assertions)
- [Email Assertions](#email-assertions)
- [URL Assertions](#url-assertions)
- [Standard Python Assertions](#standard-python-assertions)

## Response Assertions

### assertContains()

Tests that a response contains specific text or HTML.

```python
def test_article_detail_contains_title(self):
    article = Article.objects.create(title='My Article')
    response = self.client.get(f'/articles/{article.pk}/')

    # Check for text in response
    self.assertContains(response, 'My Article')

    # Check for HTML
    self.assertContains(response, '<h1>My Article</h1>', html=True)

    # Check count
    self.assertContains(response, 'article', count=3)

    # Verify status code (default: 200)
    self.assertContains(response, 'text', status_code=200)
```

**Parameters:**
- `response`: Response object
- `text`: String or bytes to search for
- `count` (optional): Expected number of occurrences
- `status_code` (optional): Expected status code (default: 200)
- `msg_prefix` (optional): Custom error message prefix
- `html` (optional): If True, compare as HTML (ignores whitespace/formatting)

**Common Uses:**
```python
# Check for specific content
self.assertContains(response, 'Welcome, user@example.com')

# Verify HTML structure
self.assertContains(
    response,
    '<div class="alert">Success</div>',
    html=True
)

# Count occurrences
self.assertContains(response, 'Article', count=10)  # 10 articles listed
```

### assertNotContains()

Tests that a response does NOT contain specific text.

```python
def test_draft_not_visible_to_public(self):
    draft = Article.objects.create(title='Draft', published=False)
    response = self.client.get('/articles/')

    self.assertNotContains(response, 'Draft')

# With custom status code
def test_deleted_article_not_found(self):
    response = self.client.get('/articles/999/')
    self.assertNotContains(response, 'Article', status_code=404)
```

### assertRedirects()

Tests that a response redirects to a specific URL.

```python
def test_login_required_redirects_to_login(self):
    response = self.client.get('/profile/')

    # Basic redirect check
    self.assertRedirects(response, '/login/')

    # Check redirect with query parameters
    self.assertRedirects(
        response,
        '/login/?next=/profile/'
    )

    # Follow redirect chain
    self.assertRedirects(
        response,
        '/final-destination/',
        fetch_redirect_response=True
    )

    # Check status codes
    self.assertRedirects(
        response,
        '/moved/',
        status_code=301,        # Initial redirect
        target_status_code=200  # Final page
    )
```

**Parameters:**
- `response`: Response object
- `expected_url`: Expected redirect URL
- `status_code`: Expected redirect status (default: 302)
- `target_status_code`: Expected final status (default: 200)
- `fetch_redirect_response`: Follow redirect chain (default: True)

**Common Patterns:**
```python
# After successful form submission
response = self.client.post('/articles/create/', data)
self.assertRedirects(response, f'/articles/{article.pk}/')

# After login
response = self.client.post('/login/', {'username': 'user', 'password': 'pass'})
self.assertRedirects(response, '/dashboard/')

# Permanent redirect
self.assertRedirects(response, '/new-url/', status_code=301)
```

### Status Code Assertions

```python
def test_response_status_codes(self):
    # 200 OK
    response = self.client.get('/articles/')
    self.assertEqual(response.status_code, 200)

    # 404 Not Found
    response = self.client.get('/articles/999/')
    self.assertEqual(response.status_code, 404)

    # 403 Forbidden
    response = self.client.get('/admin/')
    self.assertEqual(response.status_code, 403)

    # 201 Created (API)
    response = self.client.post('/api/articles/', data)
    self.assertEqual(response.status_code, 201)

    # 400 Bad Request
    response = self.client.post('/api/articles/', {})
    self.assertEqual(response.status_code, 400)
```

## Template Assertions

### assertTemplateUsed()

Tests that a specific template was used to render a response.

```python
def test_article_list_uses_correct_template(self):
    response = self.client.get('/articles/')

    # Single template
    self.assertTemplateUsed(response, 'articles/list.html')

    # Check base template was used
    self.assertTemplateUsed(response, 'base.html')

# Use as context manager
def test_template_used_in_view(self):
    with self.assertTemplateUsed('articles/detail.html'):
        self.client.get('/articles/1/')

# Multiple templates
def test_includes_partial(self):
    response = self.client.get('/articles/1/')
    self.assertTemplateUsed(response, 'articles/detail.html')
    self.assertTemplateUsed(response, 'articles/_comments.html')
```

### assertTemplateNotUsed()

Tests that a template was NOT used.

```python
def test_ajax_request_uses_partial_only(self):
    response = self.client.get(
        '/articles/',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )

    # Should use partial, not full template
    self.assertTemplateNotUsed(response, 'base.html')
    self.assertTemplateUsed(response, 'articles/_list_partial.html')
```

### Checking Template Context

```python
def test_article_detail_context(self):
    article = Article.objects.create(title='Test')
    response = self.client.get(f'/articles/{article.pk}/')

    # Check context variable exists
    self.assertIn('article', response.context)

    # Check context value
    self.assertEqual(response.context['article'], article)

    # Check context variable type
    self.assertIsInstance(response.context['articles'], list)

    # Check queryset in context
    self.assertQuerySetEqual(
        response.context['articles'],
        Article.objects.all(),
        transform=lambda x: x  # Identity function
    )
```

## Form Assertions

### assertFormError()

Tests that a form has specific validation errors (Django < 4.1).

```python
def test_article_form_validation(self):
    response = self.client.post('/articles/create/', {
        'title': '',  # Required field
        'content': 'Test content'
    })

    # Check for field error
    self.assertFormError(
        response,
        'form',           # Form name in context
        'title',          # Field name
        'This field is required.'  # Error message
    )

    # Check for non-field error
    self.assertFormError(
        response,
        'form',
        None,  # Non-field error
        'Start date must be before end date.'
    )
```

### Form Validation (Django 4.1+)

```python
def test_form_validation_modern(self):
    response = self.client.post('/articles/create/', {
        'title': '',
        'content': 'Test'
    })

    # Access form from context
    form = response.context['form']

    # Check if form is invalid
    self.assertFalse(form.is_valid())

    # Check specific field errors
    self.assertIn('title', form.errors)
    self.assertEqual(
        form.errors['title'],
        ['This field is required.']
    )

    # Check error count
    self.assertEqual(len(form.errors), 1)

def test_valid_form_submission(self):
    response = self.client.post('/articles/create/', {
        'title': 'Valid Title',
        'content': 'Valid content'
    })

    # Should redirect on success
    self.assertEqual(response.status_code, 302)

    # Verify object was created
    self.assertTrue(Article.objects.filter(title='Valid Title').exists())
```

### Form Instance Testing

```python
def test_article_form_directly(self):
    # Test form with valid data
    form = ArticleForm(data={
        'title': 'Test Article',
        'content': 'Content here'
    })
    self.assertTrue(form.is_valid())

    # Test form with invalid data
    form = ArticleForm(data={'title': ''})
    self.assertFalse(form.is_valid())
    self.assertIn('title', form.errors)

    # Test cleaned data
    form = ArticleForm(data={
        'title': '  Test  ',
        'content': 'Content'
    })
    self.assertTrue(form.is_valid())
    self.assertEqual(form.cleaned_data['title'], 'Test')  # Stripped
```

## Database Assertions

### assertQuerySetEqual()

Compares two querysets for equality.

```python
def test_published_articles_only(self):
    Article.objects.create(title='Published', published=True)
    Article.objects.create(title='Draft', published=False)

    # Get published articles
    published = Article.objects.filter(published=True)

    # Compare querysets
    self.assertQuerySetEqual(
        published,
        Article.objects.filter(published=True)
    )

    # Compare with list of objects
    self.assertQuerySetEqual(
        published,
        [Article.objects.get(title='Published')]
    )

# Ordered comparison
def test_articles_ordered_by_date(self):
    a1 = Article.objects.create(title='First', created=datetime(2024, 1, 1))
    a2 = Article.objects.create(title='Second', created=datetime(2024, 1, 2))

    self.assertQuerySetEqual(
        Article.objects.order_by('created'),
        [a1, a2],
        ordered=True  # Order matters
    )

# Transform values for comparison
def test_article_titles(self):
    Article.objects.create(title='Python')
    Article.objects.create(title='Django')

    self.assertQuerySetEqual(
        Article.objects.order_by('title'),
        ['Django', 'Python'],
        transform=lambda x: x.title
    )
```

**Modern Django 4.2+ Usage:**
```python
def test_queryset_equal_modern(self):
    Article.objects.create(title='Test 1')
    Article.objects.create(title='Test 2')

    # Simpler syntax in Django 4.2+
    self.assertQuerySetEqual(
        Article.objects.all(),
        Article.objects.all()
    )

    # With values
    self.assertQuerySetEqual(
        Article.objects.values_list('title', flat=True).order_by('title'),
        ['Test 1', 'Test 2']
    )
```

### assertNumQueries()

Tests exact number of database queries executed.

```python
def test_article_list_query_count(self):
    # Create test data
    for i in range(10):
        Article.objects.create(title=f'Article {i}')

    # Should only need 1 query
    with self.assertNumQueries(1):
        list(Article.objects.all())

def test_optimized_with_select_related(self):
    user = User.objects.create_user('user')
    for i in range(5):
        Article.objects.create(title=f'Article {i}', author=user)

    # Without select_related: 6 queries (1 + 5)
    with self.assertNumQueries(6):
        articles = Article.objects.all()
        for article in articles:
            _ = article.author.username  # Triggers query per article

    # With select_related: 1 query
    with self.assertNumQueries(1):
        articles = Article.objects.select_related('author').all()
        for article in articles:
            _ = article.author.username  # No additional queries

def test_n_plus_one_with_prefetch(self):
    for i in range(3):
        article = Article.objects.create(title=f'Article {i}')
        for j in range(2):
            Comment.objects.create(article=article, text=f'Comment {j}')

    # Without prefetch_related: 4 queries (1 + 3)
    with self.assertNumQueries(4):
        for article in Article.objects.all():
            list(article.comments.all())

    # With prefetch_related: 2 queries
    with self.assertNumQueries(2):
        for article in Article.objects.prefetch_related('comments').all():
            list(article.comments.all())
```

### Object Existence Assertions

```python
def test_article_created(self):
    Article.objects.create(title='Test')

    # Check object exists
    self.assertTrue(
        Article.objects.filter(title='Test').exists()
    )

    # Count objects
    self.assertEqual(Article.objects.count(), 1)

    # Get specific object
    article = Article.objects.get(title='Test')
    self.assertEqual(article.title, 'Test')

def test_article_deleted(self):
    article = Article.objects.create(title='Test')
    article.delete()

    # Verify deleted
    self.assertFalse(
        Article.objects.filter(pk=article.pk).exists()
    )
    self.assertEqual(Article.objects.count(), 0)
```

## Email Assertions

Django's test runner captures emails sent during tests.

```python
from django.core import mail
from django.test import TestCase

class EmailTests(TestCase):
    def test_welcome_email_sent(self):
        # Trigger email
        send_welcome_email('user@example.com')

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Check email details
        email = mail.outbox[0]
        self.assertEqual(email.subject, 'Welcome!')
        self.assertEqual(email.to, ['user@example.com'])
        self.assertEqual(email.from_email, 'noreply@example.com')
        self.assertIn('Welcome to our site', email.body)

    def test_multiple_emails(self):
        # Send multiple emails
        send_notification('user1@example.com')
        send_notification('user2@example.com')

        # Check count
        self.assertEqual(len(mail.outbox), 2)

        # Check recipients
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn('user1@example.com', recipients)
        self.assertIn('user2@example.com', recipients)

    def test_email_attachments(self):
        send_report_email('user@example.com')

        email = mail.outbox[0]
        self.assertEqual(len(email.attachments), 1)

        # Check attachment details
        filename, content, mimetype = email.attachments[0]
        self.assertEqual(filename, 'report.pdf')
        self.assertEqual(mimetype, 'application/pdf')

    def test_html_email(self):
        send_html_email('user@example.com')

        email = mail.outbox[0]
        # Check HTML alternative
        self.assertEqual(len(email.alternatives), 1)
        html_content, mimetype = email.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('<h1>Welcome</h1>', html_content)
```

**Setup and Teardown:**
```python
def setUp(self):
    # Email outbox is automatically cleared before each test
    pass

def tearDown(self):
    # Or manually clear
    mail.outbox = []
```

## URL Assertions

### URL Resolution

```python
from django.urls import reverse, resolve
from django.test import SimpleTestCase

class URLTests(SimpleTestCase):
    def test_article_detail_url_resolves(self):
        url = reverse('article-detail', args=[1])
        self.assertEqual(url, '/articles/1/')

        # Check it resolves to correct view
        resolver = resolve(url)
        self.assertEqual(resolver.view_name, 'article-detail')
        self.assertEqual(resolver.kwargs, {'pk': 1})

    def test_url_with_slug(self):
        url = reverse('article-detail', kwargs={'slug': 'test-article'})
        self.assertEqual(url, '/articles/test-article/')

    def test_namespaced_url(self):
        url = reverse('blog:article-list')
        self.assertEqual(url, '/blog/articles/')
```

### URL Patterns

```python
def test_url_pattern_matches(self):
    # Test various URL patterns work
    patterns = [
        '/articles/',
        '/articles/1/',
        '/articles/test-slug/',
        '/articles/2024/01/15/',
    ]

    for pattern in patterns:
        resolver = resolve(pattern)
        self.assertIsNotNone(resolver.view_name)
```

## Standard Python Assertions

### Equality

```python
def test_equality(self):
    article = Article.objects.create(title='Test')

    # Basic equality
    self.assertEqual(article.title, 'Test')
    self.assertNotEqual(article.title, 'Other')

    # Numeric equality
    self.assertEqual(Article.objects.count(), 1)

    # List/Dict equality
    self.assertEqual(response.json(), {'status': 'success'})
    self.assertEqual(list(queryset), [article])
```

### Truth Values

```python
def test_truth_values(self):
    article = Article.objects.create(title='Test', published=True)

    # Boolean checks
    self.assertTrue(article.published)
    self.assertFalse(article.is_draft())

    # Existence checks
    self.assertIsNotNone(article.author)
    self.assertIsNone(article.deleted_at)
```

### Membership

```python
def test_membership(self):
    article = Article.objects.create(title='Test', tags=['python', 'django'])

    # In/not in
    self.assertIn('python', article.tags)
    self.assertNotIn('ruby', article.tags)

    # Dict membership
    data = response.json()
    self.assertIn('id', data)
    self.assertIn('title', data)
```

### Comparisons

```python
def test_comparisons(self):
    article = Article.objects.create(views=100)

    # Numeric comparisons
    self.assertGreater(article.views, 50)
    self.assertGreaterEqual(article.views, 100)
    self.assertLess(article.views, 200)
    self.assertLessEqual(article.views, 100)

    # Date comparisons
    from django.utils import timezone
    now = timezone.now()
    self.assertLess(article.created_at, now)
```

### Instance Checks

```python
def test_instance_types(self):
    article = Article.objects.create(title='Test')

    # Type checks
    self.assertIsInstance(article, Article)
    self.assertIsInstance(article.title, str)
    self.assertIsInstance(article.views, int)

    # Not instance
    self.assertNotIsInstance(article, Comment)
```

### Raises Exceptions

```python
def test_exceptions(self):
    # Test that exception is raised
    with self.assertRaises(ValueError):
        Article.objects.create(title='', published=True)  # Invalid

    # Test specific exception message
    with self.assertRaisesMessage(ValueError, 'Title cannot be empty'):
        validate_article_title('')

    # Test DoesNotExist
    with self.assertRaises(Article.DoesNotExist):
        Article.objects.get(pk=999)

    # Test ValidationError
    from django.core.exceptions import ValidationError
    with self.assertRaises(ValidationError):
        article = Article(title='x' * 300)  # Too long
        article.full_clean()
```

### Regex Matching

```python
def test_regex_patterns(self):
    article = Article.objects.create(title='Test Article 123')

    # Match pattern
    self.assertRegex(article.title, r'\d+')  # Contains digits
    self.assertNotRegex(article.slug, r'\s')  # No whitespace
```

### Warnings

```python
import warnings
from django.test import TestCase

def test_deprecation_warning(self):
    # Test that warning is raised
    with self.assertWarns(DeprecationWarning):
        old_function()

    # Test warning message
    with self.assertWarnsMessage(
        DeprecationWarning,
        'This function is deprecated'
    ):
        old_function()
```

### Almost Equal (for floats)

```python
def test_float_equality(self):
    result = calculate_percentage(33, 100)

    # Exact equality fails with floats
    # self.assertEqual(result, 0.33)  # Might fail!

    # Use assertAlmostEqual instead
    self.assertAlmostEqual(result, 0.33, places=2)

    # Or with delta
    self.assertAlmostEqual(result, 0.33, delta=0.01)
```

## Custom Assertions

Create custom assertions for repeated patterns:

```python
class ArticleTestCase(TestCase):
    def assertArticleValid(self, article):
        """Custom assertion for valid article"""
        self.assertIsNotNone(article.title)
        self.assertIsNotNone(article.slug)
        self.assertIsNotNone(article.author)
        self.assertTrue(len(article.title) > 0)
        self.assertTrue(len(article.slug) > 0)

    def assertArticlePublished(self, article):
        """Custom assertion for published state"""
        self.assertTrue(article.published)
        self.assertIsNotNone(article.published_at)
        self.assertLess(article.published_at, timezone.now())

# Usage
def test_article_creation(self):
    article = Article.objects.create(
        title='Test',
        author=self.user,
        published=True
    )
    self.assertArticleValid(article)
    self.assertArticlePublished(article)
```

## Assertion Best Practices

### 1. Use Specific Assertions

```python
# ❌ BAD: Generic assertion
self.assertTrue(response.status_code == 200)

# ✅ GOOD: Specific assertion with better error message
self.assertEqual(response.status_code, 200)

# ❌ BAD
self.assertTrue('error' not in response.json())

# ✅ GOOD
self.assertNotIn('error', response.json())
```

### 2. Add Descriptive Messages

```python
# Add custom failure messages for clarity
self.assertEqual(
    response.status_code,
    200,
    f"Expected 200, got {response.status_code}. Response: {response.content}"
)

self.assertTrue(
    article.published,
    f"Article {article.pk} should be published but isn't"
)
```

### 3. One Logical Assertion Per Test

```python
# ❌ BAD: Testing multiple things
def test_article(self):
    article = Article.objects.create(title='Test')
    self.assertEqual(article.title, 'Test')
    self.assertEqual(article.slug, 'test')
    self.assertTrue(article.published)
    self.assertEqual(len(article.tags), 0)

# ✅ GOOD: Separate tests for separate concerns
def test_article_title(self):
    article = Article.objects.create(title='Test')
    self.assertEqual(article.title, 'Test')

def test_article_slug_generation(self):
    article = Article.objects.create(title='Test')
    self.assertEqual(article.slug, 'test')

def test_article_defaults_to_published(self):
    article = Article.objects.create(title='Test')
    self.assertTrue(article.published)
```

### 4. Assert Before Acting

```python
# ❌ BAD: No verification after action
def test_article_deletion(self):
    article = Article.objects.create(title='Test')
    article.delete()

# ✅ GOOD: Verify the result
def test_article_deletion(self):
    article = Article.objects.create(title='Test')
    article_pk = article.pk
    article.delete()

    # Verify it was deleted
    self.assertFalse(
        Article.objects.filter(pk=article_pk).exists()
    )
```

## Summary

**Most Common Assertions:**
- `assertEqual()` / `assertNotEqual()` - Basic equality
- `assertContains()` / `assertNotContains()` - Response content
- `assertTrue()` / `assertFalse()` - Boolean values
- `assertIn()` / `assertNotIn()` - Membership
- `assertRedirects()` - Redirect behavior
- `assertTemplateUsed()` - Template rendering
- `assertNumQueries()` - Query optimization
- `assertQuerySetEqual()` - QuerySet comparison

**Performance Testing:**
- `assertNumQueries()` - Catch N+1 queries

**Email Testing:**
- `mail.outbox` - Captured emails

**Choose the right assertion for better error messages and more maintainable tests!**
