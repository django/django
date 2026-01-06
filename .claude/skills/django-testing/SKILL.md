# Django Testing Skill

## Overview

This skill helps you write comprehensive, efficient, and maintainable tests for Django applications. It covers the full testing lifecycle from choosing the right test classes to optimizing performance and integrating with CI/CD pipelines.

**Use this skill when you need to:**
- Write tests for Django models, views, forms, and APIs
- Choose between SimpleTestCase, TestCase, TransactionTestCase, or LiveServerTestCase
- Test async views and database operations
- Mock external services and dependencies
- Optimize test performance and database operations
- Set up CI/CD pipelines with parallel test execution
- Debug slow or flaky tests
- Measure and enforce test coverage

## Quick Start

```python
# 1. Create a test file
# tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from myapp.models import Article

class ArticleViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Run once per test class - efficient for read-only data
        cls.article = Article.objects.create(
            title="Test Article",
            content="Test content"
        )

    def test_article_detail_view(self):
        # Test that article detail view works
        url = reverse('article-detail', args=[self.article.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Article")

# 2. Run tests
# python manage.py test

# 3. Run with coverage
# coverage run --source='.' manage.py test
# coverage report
```

## When to Use This Skill

**Use this skill if you need to:**
- ✅ Write unit tests for models, views, forms, or management commands
- ✅ Test HTTP endpoints and API responses
- ✅ Test database transactions and concurrent operations
- ✅ Mock external APIs or services
- ✅ Set up automated testing in CI/CD
- ✅ Optimize slow test suites
- ✅ Test async views or ORM operations

**Use other skills for:**
- ❌ Integration testing with Selenium (use django-frontend skill)
- ❌ Load testing (use performance testing tools)
- ❌ Security testing (use django-security skill)

## Core Workflows

### Workflow 1: Choose the Right Test Case Type

**Decision Tree:**

```
Does your test need database access?
├─ NO → Use SimpleTestCase
│   └─ Fastest, for testing utilities, forms, URL routing
│
└─ YES → Does it test database transactions?
    ├─ NO → Use TestCase
    │   └─ Standard choice, uses transactions for isolation
    │
    └─ YES → Does it need a live server?
        ├─ NO → Use TransactionTestCase
        │   └─ For testing transaction behavior
        │
        └─ YES → Use LiveServerTestCase
            └─ For integration tests with Selenium
```

**Examples:**

```python
# SimpleTestCase - No database
from django.test import SimpleTestCase

class URLTests(SimpleTestCase):
    def test_homepage_url_resolves(self):
        url = reverse('home')
        self.assertEqual(url, '/')

# TestCase - Standard database tests
from django.test import TestCase

class ArticleModelTests(TestCase):
    def test_article_creation(self):
        article = Article.objects.create(title="Test")
        self.assertEqual(article.title, "Test")

# TransactionTestCase - Test transaction behavior
from django.test import TransactionTestCase

class PaymentTests(TransactionTestCase):
    def test_payment_rollback(self):
        # Test that failed payments rollback correctly
        with transaction.atomic():
            payment = Payment.objects.create(amount=100)
            # Simulate failure
            raise ValueError("Payment failed")

# LiveServerTestCase - Integration with Selenium
from django.test import LiveServerTestCase
from selenium import webdriver

class BrowserTests(LiveServerTestCase):
    def setUp(self):
        self.browser = webdriver.Chrome()

    def test_user_flow(self):
        self.browser.get(self.live_server_url)
        # Test user interactions
```

**See:** [reference/test_classes.md](reference/test_classes.md) for complete hierarchy and examples.

### Workflow 2: Test API Endpoints

**Steps:**

1. **Set up test data efficiently**
2. **Use the test client**
3. **Assert response structure**
4. **Test authentication and permissions**

```python
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
import json

User = get_user_model()

class ArticleAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create once, use in all tests
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.article = Article.objects.create(
            title="Test Article",
            author=cls.user,
            published=True
        )

    def setUp(self):
        # Create fresh client for each test
        self.client = APIClient()

    def test_list_articles(self):
        """Test listing all articles"""
        url = reverse('article-list')
        response = self.client.get(url)

        # Assert status code
        self.assertEqual(response.status_code, 200)

        # Assert response structure
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)

        # Assert content
        self.assertEqual(data[0]['title'], "Test Article")

    def test_create_article_requires_auth(self):
        """Test that creating articles requires authentication"""
        url = reverse('article-list')
        data = {'title': 'New Article', 'content': 'Content'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 401)

    def test_create_article_authenticated(self):
        """Test creating article as authenticated user"""
        self.client.force_authenticate(user=self.user)

        url = reverse('article-list')
        data = {
            'title': 'New Article',
            'content': 'Content here'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Article.objects.count(), 2)

        # Verify response data
        self.assertEqual(response.json()['title'], 'New Article')
```

**See:** [reference/assertions.md](reference/assertions.md) for all assertion methods.

### Workflow 3: Optimize Test Data with setUpTestData

**Problem:** Creating database objects in `setUp()` is slow because it runs before every test.

**Solution:** Use `setUpTestData()` for read-only test data.

```python
class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Run ONCE per test class (not per test method).
        Use for data that won't be modified by tests.
        """
        # Create multiple objects efficiently
        cls.author = User.objects.create_user(
            username='author',
            email='author@example.com'
        )

        # Bulk create for better performance
        cls.articles = Article.objects.bulk_create([
            Article(title=f"Article {i}", author=cls.author)
            for i in range(10)
        ])

        # Store single object for convenience
        cls.article = cls.articles[0]

    def setUp(self):
        """
        Runs BEFORE EACH test method.
        Use for mutable state or per-test setup.
        """
        self.client = Client()

    def test_article_list(self):
        # cls.articles available here
        response = self.client.get('/articles/')
        self.assertEqual(len(response.context['articles']), 10)

    def test_article_detail(self):
        # cls.article available here
        response = self.client.get(f'/articles/{self.article.pk}/')
        self.assertEqual(response.status_code, 200)

# Performance comparison:
# setUp() for 100 tests with 5 objects each = 500 DB operations
# setUpTestData() for 100 tests = 5 DB operations (100x faster!)
```

**Important Notes:**
- Data in `setUpTestData()` is wrapped in a transaction and rolled back after the class
- Modifications to objects will persist within the same test but not across tests
- For mutable data that changes per test, use `setUp()` instead
- Use `bulk_create()` for creating many objects efficiently

**See:** [scripts/detect_slow_tests.py](scripts/detect_slow_tests.py) to identify tests that should use `setUpTestData()`.

### Workflow 4: Mock External Services

**When to Mock:**
- External API calls (payment gateways, email services, third-party APIs)
- Time-dependent behavior (datetime.now(), timezone.now())
- File system operations
- Network requests

```python
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase
from myapp.services import PaymentService
from myapp.models import Order

class PaymentTests(TestCase):
    @patch('myapp.services.stripe.Charge.create')
    def test_successful_payment(self, mock_charge):
        """Mock Stripe API call"""
        # Configure mock return value
        mock_charge.return_value = Mock(
            id='ch_123',
            status='succeeded',
            amount=1000
        )

        order = Order.objects.create(total=10.00)
        service = PaymentService()
        result = service.process_payment(order, token='tok_test')

        # Assert mock was called correctly
        mock_charge.assert_called_once_with(
            amount=1000,
            currency='usd',
            source='tok_test'
        )

        # Assert business logic
        self.assertTrue(result.success)
        self.assertEqual(result.charge_id, 'ch_123')

    @patch('myapp.services.send_email')
    def test_order_confirmation_email(self, mock_send_email):
        """Mock email sending"""
        order = Order.objects.create(
            user_email='test@example.com',
            total=50.00
        )

        order.send_confirmation()

        # Assert email was sent
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertIn('test@example.com', args)
        self.assertIn('Order Confirmation', kwargs['subject'])

    @patch('django.utils.timezone.now')
    def test_time_dependent_behavior(self, mock_now):
        """Mock current time"""
        from datetime import datetime, timezone

        # Set specific time
        fixed_time = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        mock_now.return_value = fixed_time

        article = Article.objects.create(title="Test")
        self.assertEqual(article.created_at, fixed_time)
```

**Advanced Mocking Patterns:**

```python
# Mock multiple methods on same object
@patch.object(ExternalService, 'authenticate')
@patch.object(ExternalService, 'fetch_data')
def test_service_integration(self, mock_fetch, mock_auth):
    mock_auth.return_value = {'token': 'abc123'}
    mock_fetch.return_value = {'data': 'test'}
    # Test code here

# Context manager for temporary mocking
def test_with_context_manager(self):
    with patch('myapp.utils.external_api_call') as mock_api:
        mock_api.return_value = {'status': 'ok'}
        # Mock only active within this block
        result = my_function()
        self.assertEqual(result, expected)

# Mock class instances
@patch('myapp.services.ExternalClient')
def test_client_usage(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.get_data.return_value = {'key': 'value'}

    service = MyService()
    result = service.fetch_data()

    mock_instance.get_data.assert_called_once()
```

**See:** [reference/mocking.md](reference/mocking.md) for comprehensive patterns.

### Workflow 5: Measure Test Coverage

**Steps:**

1. **Install coverage**
   ```bash
   pip install coverage
   ```

2. **Run tests with coverage**
   ```bash
   # Collect coverage data
   coverage run --source='.' manage.py test

   # Generate report
   coverage report

   # Generate HTML report
   coverage html
   open htmlcov/index.html
   ```

3. **Configure coverage** (`.coveragerc`)
   ```ini
   [run]
   source = .
   omit =
       */migrations/*
       */tests/*
       */test_*.py
       manage.py
       */venv/*
       */virtualenv/*

   [report]
   exclude_lines =
       pragma: no cover
       def __repr__
       raise AssertionError
       raise NotImplementedError
       if __name__ == .__main__.:
       if TYPE_CHECKING:
   ```

4. **Enforce minimum coverage**
   ```bash
   # Fail if coverage below 80%
   coverage report --fail-under=80
   ```

5. **Identify untested code**
   ```bash
   # Show missing lines
   coverage report --show-missing

   # Focus on specific app
   coverage report --include="myapp/*"
   ```

**Example Output:**
```
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
myapp/models.py              45      2    96%   67-68
myapp/views.py               89      8    91%   45, 67-73
myapp/forms.py               34      0   100%
myapp/utils.py               23      5    78%   12-16
-------------------------------------------------------
TOTAL                       191     15    92%
```

**CI/CD Integration:**
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    coverage run --source='.' manage.py test
    coverage report --fail-under=80
    coverage xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

**See:** [reference/ci_cd.md](reference/ci_cd.md) for full CI/CD patterns.

## Test Class Decision Tree

```
┌─────────────────────────────────────┐
│   What are you testing?             │
└──────────────┬──────────────────────┘
               │
               ├─ URL routing, form validation (no DB)
               │  → SimpleTestCase
               │
               ├─ Models, standard views, APIs
               │  → TestCase (default choice)
               │     │
               │     └─ Need to test transaction.atomic()?
               │        → TransactionTestCase
               │
               ├─ Async views or ORM operations
               │  → Use async test methods with TestCase
               │     See: reference/async_testing.md
               │
               ├─ Integration tests with browser
               │  → LiveServerTestCase + Selenium
               │
               └─ External dependencies?
                  → Use @patch decorators with any test class
                     See: reference/mocking.md
```

## Scripts & Tools

### Generate Test Boilerplate

```bash
# Generate tests for a model
python .claude/skills/django-testing/scripts/generate_tests.py \
    --model myapp/models.py:Article \
    --output myapp/tests/test_article.py

# Generate tests for a view
python .claude/skills/django-testing/scripts/generate_tests.py \
    --view myapp/views.py:ArticleDetailView \
    --output myapp/tests/test_views.py
```

### Detect Slow Tests

```bash
# Find tests taking >1 second
python .claude/skills/django-testing/scripts/detect_slow_tests.py \
    --threshold 1.0

# Analyze query counts
python .claude/skills/django-testing/scripts/detect_slow_tests.py \
    --check-queries

# Generate optimization report
python .claude/skills/django-testing/scripts/detect_slow_tests.py \
    --report optimization_report.json
```

## Common Patterns

### Pattern 1: Testing Forms

```python
from django.test import TestCase
from myapp.forms import ContactForm

class ContactFormTests(TestCase):
    def test_valid_form(self):
        form_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'message': 'Hello world'
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_required_field(self):
        form_data = {'name': 'John Doe'}
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_email(self):
        form_data = {
            'name': 'John',
            'email': 'invalid-email',
            'message': 'Test'
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['email'], ['Enter a valid email address.'])
```

### Pattern 2: Testing Management Commands

```python
from django.core.management import call_command
from django.test import TestCase
from io import StringIO

class CommandTests(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command('mycommand', '--option=value', stdout=out)
        self.assertIn('Success', out.getvalue())

    def test_command_creates_objects(self):
        call_command('import_data', 'test_data.csv')
        self.assertEqual(Article.objects.count(), 10)
```

### Pattern 3: Testing Permissions

```python
class ArticlePermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user', 'user@test.com', 'pass')
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.article = Article.objects.create(title="Test", author=self.admin)

    def test_anonymous_cannot_create(self):
        response = self.client.post('/articles/create/', {'title': 'Test'})
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_user_can_create(self):
        self.client.force_login(self.user)
        response = self.client.post('/articles/create/', {
            'title': 'My Article',
            'content': 'Content here'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Article.objects.filter(title='My Article').exists())

    def test_user_cannot_edit_others_articles(self):
        self.client.force_login(self.user)
        url = f'/articles/{self.article.pk}/edit/'
        response = self.client.post(url, {'title': 'Modified'})
        self.assertEqual(response.status_code, 403)
```

## Anti-Patterns

### ❌ Anti-Pattern 1: Creating Objects in setUp() for Read-Only Tests

```python
# BAD: Slow - creates objects before EVERY test
class ArticleTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(title="Test")

    def test_article_str(self):
        self.assertEqual(str(self.article), "Test")

    def test_article_slug(self):
        self.assertEqual(self.article.slug, "test")

# GOOD: Fast - creates objects ONCE per class
class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.article = Article.objects.create(title="Test")

    def test_article_str(self):
        self.assertEqual(str(self.article), "Test")

    def test_article_slug(self):
        self.assertEqual(self.article.slug, "test")
```

### ❌ Anti-Pattern 2: Not Using assertNumQueries

```python
# BAD: Hidden N+1 query problem
def test_article_list(self):
    for i in range(10):
        Article.objects.create(title=f"Article {i}")

    response = self.client.get('/articles/')
    self.assertEqual(response.status_code, 200)

# GOOD: Catches query inefficiencies
def test_article_list(self):
    for i in range(10):
        Article.objects.create(title=f"Article {i}")

    # Should only need 1 query for list
    with self.assertNumQueries(1):
        response = self.client.get('/articles/')
    self.assertEqual(response.status_code, 200)
```

### ❌ Anti-Pattern 3: Testing Django's Built-in Functionality

```python
# BAD: Testing Django's ORM
def test_create_article(self):
    article = Article.objects.create(title="Test")
    self.assertEqual(Article.objects.count(), 1)

# GOOD: Test your business logic
def test_article_auto_generates_slug(self):
    article = Article.objects.create(title="Test Article")
    self.assertEqual(article.slug, "test-article")

def test_article_published_manager(self):
    Article.objects.create(title="Draft", published=False)
    Article.objects.create(title="Published", published=True)
    self.assertEqual(Article.published.count(), 1)
```

### ❌ Anti-Pattern 4: Not Mocking External Services

```python
# BAD: Makes real API calls (slow, flaky, costs money)
def test_send_confirmation_email(self):
    order = Order.objects.create(user_email='test@example.com')
    order.send_confirmation()  # Calls SendGrid API!
    # How do we verify it worked?

# GOOD: Mock external dependencies
@patch('myapp.services.sendgrid.send_email')
def test_send_confirmation_email(self, mock_send):
    order = Order.objects.create(user_email='test@example.com')
    order.send_confirmation()

    mock_send.assert_called_once_with(
        to='test@example.com',
        subject='Order Confirmation',
        template='order_confirmation'
    )
```

### ❌ Anti-Pattern 5: Vague Test Names

```python
# BAD: Unclear what's being tested
def test_article(self):
    article = Article.objects.create(title="Test")
    self.assertTrue(article)

def test_view(self):
    response = self.client.get('/articles/')
    self.assertEqual(response.status_code, 200)

# GOOD: Descriptive names
def test_article_str_returns_title(self):
    article = Article.objects.create(title="My Article")
    self.assertEqual(str(article), "My Article")

def test_article_list_view_returns_published_articles_only(self):
    Article.objects.create(title="Draft", published=False)
    Article.objects.create(title="Published", published=True)

    response = self.client.get('/articles/')
    articles = response.context['articles']
    self.assertEqual(len(articles), 1)
    self.assertEqual(articles[0].title, "Published")
```

## Edge Cases & Gotchas

### Gotcha 1: Database Resets Between Tests

```python
class ArticleTests(TestCase):
    def test_create_article(self):
        Article.objects.create(title="Test")
        self.assertEqual(Article.objects.count(), 1)

    def test_another_operation(self):
        # Database is reset! Count is 0, not 1
        self.assertEqual(Article.objects.count(), 0)
```

### Gotcha 2: Modifying setUpTestData Objects

```python
class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.article = Article.objects.create(title="Original")

    def test_modify_article(self):
        self.article.title = "Modified"
        self.article.save()
        self.assertEqual(self.article.title, "Modified")

    def test_check_article(self):
        # Still "Modified" because same object in memory!
        # Refresh from DB to get original state
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Original")
```

### Gotcha 3: File Uploads in Tests

```python
from django.core.files.uploadedfile import SimpleUploadedFile

def test_image_upload(self):
    # Create fake file
    image = SimpleUploadedFile(
        "test.jpg",
        b"fake image content",
        content_type="image/jpeg"
    )

    article = Article.objects.create(
        title="Test",
        image=image
    )

    self.assertTrue(article.image)

    # Clean up if using FileSystemStorage
    article.image.delete()
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
        django-version: [4.2, 5.0, 5.1]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install Django==${{ matrix.django-version }}
        pip install -r requirements.txt
        pip install coverage

    - name: Run tests
      run: |
        coverage run --source='.' manage.py test
        coverage report --fail-under=80
        coverage xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

**See:** [reference/ci_cd.md](reference/ci_cd.md) for parallel execution, test sharding, and advanced patterns.

## Related Skills

- **django-models**: Test model methods, managers, and querysets
- **django-views**: Test view logic and response handling
- **django-forms**: Test form validation and cleaning
- **django-admin**: Test admin customizations
- **django-commands**: Test management command behavior

## Reference Files

- [reference/test_classes.md](reference/test_classes.md) - Complete test class hierarchy and when to use each
- [reference/assertions.md](reference/assertions.md) - All Django test assertions with examples
- [reference/mocking.md](reference/mocking.md) - Comprehensive mocking patterns
- [reference/async_testing.md](reference/async_testing.md) - Testing async views and ORM operations
- [reference/ci_cd.md](reference/ci_cd.md) - CI/CD patterns, parallel testing, sharding

## Django Version Notes

**Django 4.1+:**
- Async test methods supported natively
- Use `async def test_*` for async views

**Django 4.2+ (LTS):**
- Improved async ORM support
- `assertQuerySetEqual()` improvements

**Django 5.0+:**
- New assertion methods for better error messages
- Facets in admin (requires new testing patterns)

## Troubleshooting

### Problem: Tests are slow

**Solution:** Use [scripts/detect_slow_tests.py](scripts/detect_slow_tests.py) to identify bottlenecks.
- Move read-only setup to `setUpTestData()`
- Use `bulk_create()` instead of individual `create()` calls
- Mock external services
- Check for N+1 queries with `assertNumQueries()`

### Problem: Flaky tests (pass/fail randomly)

**Solutions:**
- Mock `timezone.now()` for time-dependent tests
- Use `TransactionTestCase` if testing transaction behavior
- Avoid relying on query ordering without explicit `order_by()`
- Clear caches between tests if using Django's cache framework

### Problem: Database errors in parallel tests

**Solution:** Each worker needs its own database.
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'test_db'),
        'TEST': {
            'NAME': 'test_db_' + os.environ.get('WORKER_ID', '1')
        }
    }
}
```
