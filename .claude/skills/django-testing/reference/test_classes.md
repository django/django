# Django Test Class Hierarchy

Complete guide to Django's test class hierarchy and when to use each class.

## Table of Contents

- [Overview](#overview)
- [SimpleTestCase](#simpletestcase)
- [TestCase](#testcase)
- [TransactionTestCase](#transactiontestcase)
- [LiveServerTestCase](#liveservertestcase)
- [Comparison Matrix](#comparison-matrix)
- [Decision Guide](#decision-guide)

## Overview

Django provides a hierarchy of test case classes, each with different capabilities and performance characteristics:

```
unittest.TestCase (Python standard library)
    └── SimpleTestCase (No database)
            ├── TestCase (Database with transactions)
            └── TransactionTestCase (Database without transactions)
                    └── LiveServerTestCase (Live server for integration tests)
```

**Quick Selection Guide:**
- No database needed → `SimpleTestCase`
- Standard database tests → `TestCase` (99% of cases)
- Testing transaction behavior → `TransactionTestCase`
- Integration with Selenium → `LiveServerTestCase`

## SimpleTestCase

**Use when:** Testing code that doesn't require database access.

**Features:**
- ✅ Fastest test execution
- ✅ URL routing tests
- ✅ Form validation (without model forms that save)
- ✅ Template rendering
- ✅ Utility functions
- ❌ No database access allowed (raises error)

**Performance:** ~100x faster than TestCase for non-DB operations.

### Basic Example

```python
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from myapp.views import home_view
from myapp.forms import ContactForm

class URLTests(SimpleTestCase):
    def test_home_url_resolves(self):
        """Test URL resolves to correct view"""
        url = reverse('home')
        self.assertEqual(resolve(url).func, home_view)

    def test_article_detail_url_pattern(self):
        """Test parameterized URL patterns"""
        url = reverse('article-detail', args=[123])
        self.assertEqual(url, '/articles/123/')

class FormValidationTests(SimpleTestCase):
    def test_contact_form_valid_data(self):
        """Test form with valid data"""
        form = ContactForm(data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'message': 'Hello world'
        })
        self.assertTrue(form.is_valid())

    def test_contact_form_missing_email(self):
        """Test form validation catches missing required field"""
        form = ContactForm(data={
            'name': 'John Doe',
            'message': 'Hello'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_contact_form_invalid_email(self):
        """Test email format validation"""
        form = ContactForm(data={
            'name': 'John',
            'email': 'not-an-email',
            'message': 'Test'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('Enter a valid email address', str(form.errors['email']))
```

### Template Rendering Tests

```python
from django.test import SimpleTestCase
from django.template import Context, Template

class TemplateTagTests(SimpleTestCase):
    def test_custom_filter(self):
        """Test custom template filter"""
        template = Template('{{ value|my_filter }}')
        context = Context({'value': 'hello'})
        output = template.render(context)
        self.assertEqual(output, 'HELLO')

    def test_custom_tag(self):
        """Test custom template tag"""
        template = Template('{% load my_tags %}{% my_tag "test" %}')
        output = template.render(Context())
        self.assertIn('test', output)
```

### Utility Function Tests

```python
from django.test import SimpleTestCase
from myapp.utils import slugify_title, calculate_reading_time

class UtilityTests(SimpleTestCase):
    def test_slugify_title(self):
        """Test slug generation from title"""
        self.assertEqual(slugify_title('Hello World'), 'hello-world')
        self.assertEqual(slugify_title('Test & Title!'), 'test-title')

    def test_calculate_reading_time(self):
        """Test reading time calculation"""
        text = 'word ' * 200  # 200 words
        self.assertEqual(calculate_reading_time(text), 1)  # 1 minute

        text = 'word ' * 600  # 600 words
        self.assertEqual(calculate_reading_time(text), 3)  # 3 minutes
```

### Important Notes

**Database Access Error:**
```python
class BadTest(SimpleTestCase):
    def test_with_database(self):
        # This will raise an error!
        Article.objects.create(title="Test")
        # Error: Database access not allowed, use TestCase instead
```

**Override if Absolutely Necessary:**
```python
class SimpleTestWithDB(SimpleTestCase):
    # NOT RECOMMENDED - use TestCase instead
    databases = '__all__'

    def test_something(self):
        # Now database access is allowed, but defeats the purpose
        pass
```

## TestCase

**Use when:** Standard database tests (99% of your tests should use this).

**Features:**
- ✅ Full database access
- ✅ Fast test isolation via transactions
- ✅ Test fixtures support
- ✅ `setUpTestData()` for performance
- ✅ Test client included
- ⚠️ Each test wrapped in transaction and rolled back
- ❌ Cannot test transaction behavior (use TransactionTestCase)

**Performance:** Tests are isolated via atomic transactions (rollback after each test).

### Basic Example

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from myapp.models import Article, Comment

User = get_user_model()

class ArticleModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Run once per test class - optimal for read-only data"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        cls.article = Article.objects.create(
            title='Test Article',
            content='Test content',
            author=cls.user
        )

    def test_article_str_representation(self):
        """Test __str__ method"""
        self.assertEqual(str(self.article), 'Test Article')

    def test_article_absolute_url(self):
        """Test get_absolute_url method"""
        expected_url = f'/articles/{self.article.pk}/'
        self.assertEqual(self.article.get_absolute_url(), expected_url)

    def test_article_slug_auto_generated(self):
        """Test slug is automatically generated"""
        article = Article.objects.create(
            title='New Article',
            author=self.user
        )
        self.assertEqual(article.slug, 'new-article')

    def test_article_published_manager(self):
        """Test custom manager returns only published articles"""
        # Create unpublished article
        Article.objects.create(
            title='Draft',
            author=self.user,
            published=False
        )

        # Only one article is published (from setUpTestData)
        self.assertEqual(Article.published.count(), 1)
        self.assertEqual(Article.objects.count(), 2)
```

### View Testing with TestCase

```python
from django.test import TestCase, Client
from django.urls import reverse

class ArticleViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('user', 'user@test.com', 'pass')
        cls.article = Article.objects.create(
            title='Test Article',
            content='Content here',
            author=cls.user,
            published=True
        )

    def setUp(self):
        """Create fresh client for each test"""
        self.client = Client()

    def test_article_list_view(self):
        """Test article list view returns 200"""
        response = self.client.get(reverse('article-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Article')
        self.assertTemplateUsed(response, 'articles/list.html')

    def test_article_detail_view(self):
        """Test article detail view"""
        url = reverse('article-detail', args=[self.article.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['article'], self.article)
        self.assertContains(response, 'Test Article')

    def test_article_create_view_requires_login(self):
        """Test create view requires authentication"""
        url = reverse('article-create')
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_article_create_view_authenticated(self):
        """Test authenticated user can create article"""
        self.client.force_login(self.user)

        url = reverse('article-create')
        response = self.client.post(url, {
            'title': 'New Article',
            'content': 'New content'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Verify article was created
        article = Article.objects.get(title='New Article')
        self.assertEqual(article.author, self.user)
        self.assertEqual(article.content, 'New content')
```

### Using Fixtures

```python
from django.test import TestCase

class ArticleTestsWithFixtures(TestCase):
    fixtures = ['users.json', 'articles.json']

    def test_fixture_data_loaded(self):
        """Test fixtures loaded correctly"""
        self.assertEqual(Article.objects.count(), 10)
        self.assertEqual(User.objects.count(), 3)

    def test_specific_fixture_data(self):
        """Test specific object from fixture"""
        article = Article.objects.get(pk=1)
        self.assertEqual(article.title, 'Expected Title')
```

### Performance: setUpTestData vs setUp

```python
class SlowTests(TestCase):
    def setUp(self):
        """BAD: Runs before EVERY test - 100 tests = 100 DB writes"""
        self.user = User.objects.create_user('user', 'user@test.com', 'pass')

    # ... 100 test methods that only READ self.user

class FastTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """GOOD: Runs ONCE per class - 100 tests = 1 DB write"""
        cls.user = User.objects.create_user('user', 'user@test.com', 'pass')

    # ... 100 test methods that only READ cls.user
    # ~100x faster!
```

### Query Optimization Testing

```python
class ArticleQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('user', 'user@test.com', 'pass')
        # Create 10 articles with 5 comments each
        for i in range(10):
            article = Article.objects.create(
                title=f'Article {i}',
                author=cls.user
            )
            for j in range(5):
                Comment.objects.create(
                    article=article,
                    text=f'Comment {j}',
                    author=cls.user
                )

    def test_article_list_without_select_related(self):
        """BAD: N+1 query problem"""
        # This will generate 1 query for articles + 10 queries for authors
        articles = Article.objects.all()
        for article in articles:
            _ = article.author.username  # Triggers query per article

    def test_article_list_with_select_related(self):
        """GOOD: Optimized with select_related"""
        # Only 1 query total
        with self.assertNumQueries(1):
            articles = Article.objects.select_related('author').all()
            for article in articles:
                _ = article.author.username  # No additional queries

    def test_articles_with_comments_prefetch(self):
        """GOOD: Optimized with prefetch_related"""
        # Only 2 queries: 1 for articles, 1 for all comments
        with self.assertNumQueries(2):
            articles = Article.objects.prefetch_related('comments').all()
            for article in articles:
                _ = list(article.comments.all())  # No additional queries
```

## TransactionTestCase

**Use when:** Testing transaction-specific behavior (commit, rollback, atomic blocks).

**Features:**
- ✅ Full database access
- ✅ Can test `transaction.atomic()` behavior
- ✅ Can test real commits and rollbacks
- ✅ Multiple database support
- ⚠️ Much slower than TestCase (truncates tables between tests)
- ❌ Cannot use `setUpTestData()`

**Performance:** 10-100x slower than TestCase due to table truncation.

### When to Use TransactionTestCase

```python
from django.test import TransactionTestCase
from django.db import transaction
from myapp.models import Order, Payment

class PaymentTransactionTests(TransactionTestCase):
    def test_payment_rollback_on_error(self):
        """Test that failed payments rollback properly"""
        order = Order.objects.create(total=100.00)

        # Simulate payment processing that fails
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    order=order,
                    amount=100.00,
                    status='pending'
                )

                # Simulate payment gateway error
                raise ValueError("Payment gateway error")

        except ValueError:
            pass

        # Payment should have been rolled back
        self.assertEqual(Payment.objects.count(), 0)
        # But order should still exist
        self.assertEqual(Order.objects.count(), 1)

    def test_partial_payment_commit(self):
        """Test partial payment commits correctly"""
        order = Order.objects.create(total=100.00)

        # Create partial payment
        with transaction.atomic():
            payment = Payment.objects.create(
                order=order,
                amount=50.00,
                status='completed'
            )

        # Should be committed
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.first().amount, 50.00)

    def test_concurrent_modifications(self):
        """Test handling of concurrent modifications"""
        article = Article.objects.create(title='Test', views=0)

        # Simulate two concurrent requests updating views
        with transaction.atomic():
            a1 = Article.objects.get(pk=article.pk)
            a1.views += 1
            a1.save()

        with transaction.atomic():
            a2 = Article.objects.get(pk=article.pk)
            a2.views += 1
            a2.save()

        article.refresh_from_db()
        self.assertEqual(article.views, 2)
```

### Testing Database-Level Constraints

```python
from django.db import IntegrityError

class DatabaseConstraintTests(TransactionTestCase):
    def test_unique_constraint_violation(self):
        """Test unique constraint is enforced at database level"""
        User.objects.create_user('user1', 'user1@test.com', 'pass')

        with self.assertRaises(IntegrityError):
            # Try to create duplicate username
            with transaction.atomic():
                User.objects.create_user('user1', 'user2@test.com', 'pass')

    def test_foreign_key_constraint(self):
        """Test foreign key constraint enforcement"""
        # Cannot create comment without article
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Comment.objects.create(
                    article_id=99999,  # Non-existent article
                    text='Test'
                )
```

### Multi-Database Testing

```python
class MultiDatabaseTests(TransactionTestCase):
    # Specify which databases to reset between tests
    databases = {'default', 'analytics'}

    def test_data_sync_between_databases(self):
        """Test syncing data between databases"""
        # Create in default database
        article = Article.objects.using('default').create(
            title='Test Article'
        )

        # Sync to analytics database
        sync_to_analytics(article)

        # Verify in analytics database
        analytics_article = Article.objects.using('analytics').get(
            pk=article.pk
        )
        self.assertEqual(analytics_article.title, 'Test Article')
```

### Important: When NOT to Use TransactionTestCase

```python
# DON'T use TransactionTestCase for standard tests
class BadUsage(TransactionTestCase):  # Should be TestCase!
    def test_article_creation(self):
        """This doesn't need TransactionTestCase"""
        article = Article.objects.create(title='Test')
        self.assertEqual(article.title, 'Test')

# DO use TestCase for standard tests
class GoodUsage(TestCase):
    def test_article_creation(self):
        """Standard test - use TestCase"""
        article = Article.objects.create(title='Test')
        self.assertEqual(article.title, 'Test')
```

## LiveServerTestCase

**Use when:** Integration testing with a real browser (Selenium, Playwright).

**Features:**
- ✅ Starts a live Django server in background
- ✅ Works with Selenium/Playwright for browser testing
- ✅ Tests full request/response cycle
- ✅ Includes all TransactionTestCase features
- ⚠️ Very slow (starts server for each test class)
- ⚠️ Requires browser driver (chromedriver, geckodriver)

**Performance:** Slowest option - use sparingly for critical user flows only.

### Basic Selenium Example

```python
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class UserFlowTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = webdriver.Chrome()
        cls.browser.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_user_registration_flow(self):
        """Test complete user registration"""
        # Navigate to registration page
        self.browser.get(f'{self.live_server_url}/register/')

        # Fill out form
        self.browser.find_element(By.NAME, 'username').send_keys('newuser')
        self.browser.find_element(By.NAME, 'email').send_keys('new@example.com')
        self.browser.find_element(By.NAME, 'password1').send_keys('testpass123')
        self.browser.find_element(By.NAME, 'password2').send_keys('testpass123')

        # Submit form
        self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Wait for redirect to home page
        WebDriverWait(self.browser, 10).until(
            EC.url_contains('/home/')
        )

        # Verify user is logged in
        self.assertIn('Welcome, newuser', self.browser.page_source)

        # Verify user was created in database
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_article_search_functionality(self):
        """Test JavaScript-powered search"""
        # Create test data
        Article.objects.create(title='Python Testing', content='...')
        Article.objects.create(title='Django Models', content='...')

        # Navigate to search page
        self.browser.get(f'{self.live_server_url}/articles/')

        # Type in search box (triggers AJAX)
        search_box = self.browser.find_element(By.ID, 'search')
        search_box.send_keys('Python')

        # Wait for AJAX results
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'search-result'))
        )

        # Verify results
        results = self.browser.find_elements(By.CLASS_NAME, 'search-result')
        self.assertEqual(len(results), 1)
        self.assertIn('Python Testing', results[0].text)
```

### Testing JavaScript Interactions

```python
class JavaScriptTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = webdriver.Chrome()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_dynamic_form_fields(self):
        """Test JavaScript adds form fields dynamically"""
        self.browser.get(f'{self.live_server_url}/forms/dynamic/')

        # Initially one field
        fields = self.browser.find_elements(By.CLASS_NAME, 'form-field')
        self.assertEqual(len(fields), 1)

        # Click "Add Field" button
        add_button = self.browser.find_element(By.ID, 'add-field')
        add_button.click()

        # Wait for new field to appear
        WebDriverWait(self.browser, 10).until(
            lambda driver: len(driver.find_elements(By.CLASS_NAME, 'form-field')) == 2
        )

        # Verify second field exists
        fields = self.browser.find_elements(By.CLASS_NAME, 'form-field')
        self.assertEqual(len(fields), 2)
```

### Headless Browser for CI/CD

```python
class HeadlessTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Configure headless mode for CI
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        cls.browser = webdriver.Chrome(options=options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_page_loads(self):
        self.browser.get(f'{self.live_server_url}/')
        self.assertIn('My Site', self.browser.title)
```

## Comparison Matrix

| Feature | SimpleTestCase | TestCase | TransactionTestCase | LiveServerTestCase |
|---------|---------------|----------|---------------------|-------------------|
| Database Access | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Speed | ⚡⚡⚡ Fastest | ⚡⚡ Fast | ⚡ Slow | 🐌 Slowest |
| Transaction Support | N/A | ❌ No | ✅ Yes | ✅ Yes |
| setUpTestData | ❌ No | ✅ Yes | ❌ No | ❌ No |
| Live Server | ❌ No | ❌ No | ❌ No | ✅ Yes |
| Test Isolation | N/A | Rollback | Truncate | Truncate |
| Use Case | URLs, Forms, Utils | Standard Tests | Transactions | Browser Testing |
| Typical Speed | <0.01s | 0.1s | 1-5s | 5-30s |

## Decision Guide

### Step-by-Step Decision Process

```
1. Does your test need database access?
   NO → Use SimpleTestCase
   YES → Continue to step 2

2. Does your test need to test transaction.atomic() behavior?
   YES → Use TransactionTestCase
   NO → Continue to step 3

3. Does your test need a live server (Selenium/browser)?
   YES → Use LiveServerTestCase
   NO → Use TestCase (default choice)
```

### Examples by Use Case

#### Testing URLs and Routing
```python
# Use SimpleTestCase
class URLTests(SimpleTestCase):
    def test_url_resolves(self):
        url = reverse('article-detail', args=[1])
        self.assertEqual(url, '/articles/1/')
```

#### Testing Model Logic
```python
# Use TestCase
class ArticleTests(TestCase):
    def test_slug_generation(self):
        article = Article.objects.create(title='Test Article')
        self.assertEqual(article.slug, 'test-article')
```

#### Testing View Rendering
```python
# Use TestCase
class ViewTests(TestCase):
    def test_article_list_view(self):
        response = self.client.get('/articles/')
        self.assertEqual(response.status_code, 200)
```

#### Testing Payment Rollback
```python
# Use TransactionTestCase
class PaymentTests(TransactionTestCase):
    def test_failed_payment_rollback(self):
        with transaction.atomic():
            payment = Payment.objects.create(amount=100)
            raise Exception("Failed")  # Should rollback
```

#### Testing User Flow in Browser
```python
# Use LiveServerTestCase
class UserFlowTests(LiveServerTestCase):
    def test_login_flow(self):
        self.browser.get(f'{self.live_server_url}/login/')
        # ... Selenium interactions
```

### Common Mistakes

**Mistake 1: Using TransactionTestCase Unnecessarily**
```python
# ❌ WRONG - wastes time
class ArticleTests(TransactionTestCase):
    def test_article_creation(self):
        article = Article.objects.create(title='Test')
        self.assertTrue(article.pk)

# ✅ CORRECT - 10x faster
class ArticleTests(TestCase):
    def test_article_creation(self):
        article = Article.objects.create(title='Test')
        self.assertTrue(article.pk)
```

**Mistake 2: Using TestCase for Transaction Testing**
```python
# ❌ WRONG - won't work as expected
class PaymentTests(TestCase):
    def test_rollback(self):
        # TestCase wraps everything in a transaction already!
        # Your atomic() block won't behave like production
        with transaction.atomic():
            payment = Payment.objects.create(amount=100)
            raise Exception()

# ✅ CORRECT
class PaymentTests(TransactionTestCase):
    def test_rollback(self):
        # Now transaction.atomic() works like production
        with transaction.atomic():
            payment = Payment.objects.create(amount=100)
            raise Exception()
```

**Mistake 3: Using LiveServerTestCase for API Tests**
```python
# ❌ WRONG - unnecessarily slow
class APITests(LiveServerTestCase):
    def test_api_endpoint(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)

# ✅ CORRECT - 100x faster
class APITests(TestCase):
    def test_api_endpoint(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)
```

## Summary

**Default Choice:** Use `TestCase` for 99% of your tests.

**Special Cases:**
- **SimpleTestCase** - Non-database tests (URLs, forms, utilities)
- **TransactionTestCase** - Testing `transaction.atomic()` behavior
- **LiveServerTestCase** - Integration tests with Selenium

**Performance Impact:**
- Moving from TestCase → TransactionTestCase: 10-100x slower
- Moving from TestCase → LiveServerTestCase: 100-1000x slower

Choose wisely based on what you're actually testing!
