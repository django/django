# Mocking Patterns for Django Tests

Complete guide to mocking external dependencies in Django tests using `unittest.mock`.

## Table of Contents

- [Why Mock?](#why-mock)
- [Basic Mocking with @patch](#basic-mocking-with-patch)
- [Mock External APIs](#mock-external-apis)
- [Mock Django Components](#mock-django-components)
- [Mock Time and Dates](#mock-time-and-dates)
- [Mock File Operations](#mock-file-operations)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)

## Why Mock?

**Mock external dependencies to:**
- ✅ Make tests fast (no real API calls)
- ✅ Make tests reliable (no network failures)
- ✅ Make tests isolated (no external state)
- ✅ Test error conditions (simulate failures)
- ✅ Avoid costs (no charges for API calls)
- ✅ Enable offline testing

**Mock when:**
- Calling external APIs (Stripe, SendGrid, AWS, etc.)
- Sending emails
- Making HTTP requests
- Working with time-dependent code
- Using file system operations
- Accessing expensive resources

## Basic Mocking with @patch

### Simple Function Mocking

```python
from unittest.mock import patch, Mock
from django.test import TestCase
from myapp.services import notify_user

class NotificationTests(TestCase):
    @patch('myapp.services.send_email')
    def test_user_notification(self, mock_send_email):
        """Mock send_email function"""
        # Configure mock return value
        mock_send_email.return_value = True

        # Call function that uses send_email
        result = notify_user('user@example.com', 'Hello')

        # Verify mock was called
        mock_send_email.assert_called_once_with(
            to='user@example.com',
            subject='Notification',
            body='Hello'
        )

        # Verify result
        self.assertTrue(result)
```

### Patch Location Rules

**Important:** Patch where the object is USED, not where it's DEFINED.

```python
# myapp/services.py
from external_lib import send_sms

def notify_by_sms(phone, message):
    return send_sms(phone, message)

# tests.py - CORRECT
@patch('myapp.services.send_sms')  # Patch in services module
def test_sms_notification(self, mock_send_sms):
    notify_by_sms('+1234567890', 'Test')
    mock_send_sms.assert_called_once()

# tests.py - WRONG
@patch('external_lib.send_sms')  # Won't work!
def test_sms_notification(self, mock_send_sms):
    notify_by_sms('+1234567890', 'Test')
    # Mock was never called because we imported it differently
```

### Multiple Patches

```python
class MultiPatchTests(TestCase):
    @patch('myapp.services.send_email')
    @patch('myapp.services.send_sms')
    def test_multi_channel_notification(self, mock_sms, mock_email):
        """Multiple patches - note reverse order of parameters"""
        # Patches are applied bottom-to-top
        # Parameters are in reverse order
        mock_email.return_value = True
        mock_sms.return_value = True

        notify_user_all_channels('user@example.com', '+1234567890', 'Hi')

        mock_email.assert_called_once()
        mock_sms.assert_called_once()
```

### Context Manager Mocking

```python
def test_with_context_manager(self):
    """Use context manager for temporary mocking"""
    with patch('myapp.services.send_email') as mock_send_email:
        mock_send_email.return_value = True

        notify_user('user@example.com', 'Test')

        mock_send_email.assert_called_once()

    # Mock no longer active here
```

## Mock External APIs

### Mocking Stripe API

```python
from unittest.mock import patch, Mock
from myapp.services import PaymentService
from myapp.models import Order

class StripePaymentTests(TestCase):
    @patch('myapp.services.stripe.Charge.create')
    def test_successful_payment(self, mock_charge_create):
        """Mock Stripe charge creation"""
        # Configure mock response
        mock_charge = Mock()
        mock_charge.id = 'ch_123456'
        mock_charge.status = 'succeeded'
        mock_charge.amount = 5000
        mock_charge.currency = 'usd'
        mock_charge_create.return_value = mock_charge

        # Process payment
        order = Order.objects.create(total=50.00)
        service = PaymentService()
        result = service.charge_card(order, token='tok_test')

        # Verify mock was called correctly
        mock_charge_create.assert_called_once_with(
            amount=5000,
            currency='usd',
            source='tok_test',
            description=f'Order {order.id}'
        )

        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.charge_id, 'ch_123456')

    @patch('myapp.services.stripe.Charge.create')
    def test_payment_failure(self, mock_charge_create):
        """Mock Stripe payment failure"""
        # Simulate card declined
        import stripe
        mock_charge_create.side_effect = stripe.error.CardError(
            message='Your card was declined',
            param='card',
            code='card_declined'
        )

        order = Order.objects.create(total=50.00)
        service = PaymentService()
        result = service.charge_card(order, token='tok_test')

        # Verify error handling
        self.assertFalse(result.success)
        self.assertIn('declined', result.error_message.lower())
```

### Mocking REST API with requests

```python
@patch('myapp.services.requests.get')
def test_fetch_weather_data(self, mock_get):
    """Mock external weather API"""
    # Configure mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'temperature': 72,
        'conditions': 'sunny',
        'humidity': 45
    }
    mock_get.return_value = mock_response

    # Fetch weather
    weather = get_weather('New York')

    # Verify API was called
    mock_get.assert_called_once_with(
        'https://api.weather.com/v1/current',
        params={'location': 'New York'},
        headers={'API-Key': 'test-key'}
    )

    # Verify result
    self.assertEqual(weather['temperature'], 72)
    self.assertEqual(weather['conditions'], 'sunny')

@patch('myapp.services.requests.post')
def test_api_timeout(self, mock_post):
    """Mock API timeout"""
    import requests
    mock_post.side_effect = requests.Timeout('Connection timed out')

    with self.assertRaises(requests.Timeout):
        submit_data('http://api.example.com/data', {'key': 'value'})

@patch('myapp.services.requests.get')
def test_api_rate_limit(self, mock_get):
    """Mock API rate limiting"""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.json.return_value = {'error': 'Rate limit exceeded'}
    mock_get.return_value = mock_response

    result = fetch_user_data(user_id=123)

    self.assertIsNone(result)
    # Verify retry logic, logging, etc.
```

### Mocking AWS Services

```python
@patch('myapp.services.boto3.client')
def test_s3_file_upload(self, mock_boto3_client):
    """Mock AWS S3 upload"""
    # Configure S3 client mock
    mock_s3 = Mock()
    mock_boto3_client.return_value = mock_s3

    # Upload file
    upload_to_s3('test.txt', b'content')

    # Verify S3 client was created
    mock_boto3_client.assert_called_once_with('s3')

    # Verify upload was called
    mock_s3.put_object.assert_called_once_with(
        Bucket='my-bucket',
        Key='test.txt',
        Body=b'content'
    )

@patch('myapp.services.boto3.client')
def test_sns_notification(self, mock_boto3_client):
    """Mock AWS SNS notification"""
    mock_sns = Mock()
    mock_boto3_client.return_value = mock_sns

    send_sns_notification('Test message', topic='alerts')

    mock_sns.publish.assert_called_once_with(
        TopicArn='arn:aws:sns:us-east-1:123456789:alerts',
        Message='Test message'
    )
```

## Mock Django Components

### Mock Django Email Backend

```python
from django.core import mail
from django.test import TestCase

class EmailTests(TestCase):
    def test_welcome_email(self):
        """Django automatically mocks email backend in tests"""
        # No mocking needed - Django captures emails
        send_welcome_email('user@example.com')

        # Check captured email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['user@example.com'])
        self.assertEqual(email.subject, 'Welcome!')

# For testing email with external service like SendGrid
@patch('myapp.services.sendgrid.SendGridAPIClient')
def test_sendgrid_email(self, mock_sg_client):
    """Mock SendGrid client"""
    mock_sg = Mock()
    mock_sg_client.return_value = mock_sg

    send_email_via_sendgrid('user@example.com', 'Subject', 'Body')

    mock_sg.send.assert_called_once()
    call_args = mock_sg.send.call_args[0][0]
    self.assertEqual(call_args.to, 'user@example.com')
```

### Mock Django Cache

```python
from django.core.cache import cache
from django.test import TestCase

class CacheTests(TestCase):
    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def test_cached_data(self):
        """Test cache behavior"""
        # Cache is automatically mocked in tests (uses locmem backend)
        cache.set('key', 'value', 60)
        self.assertEqual(cache.get('key'), 'value')

@patch('myapp.services.cache.get')
@patch('myapp.services.cache.set')
def test_cache_operations(self, mock_cache_set, mock_cache_get):
    """Mock cache operations"""
    mock_cache_get.return_value = None  # Cache miss

    result = get_user_data(user_id=1)

    # Verify cache was checked
    mock_cache_get.assert_called_once_with('user_1')

    # Verify cache was set after fetch
    mock_cache_set.assert_called_once_with('user_1', result, 300)
```

### Mock Django Signals

```python
from django.test import TestCase
from unittest.mock import patch
from django.db.models.signals import post_save

class SignalTests(TestCase):
    @patch('myapp.signals.post_save_handler')
    def test_signal_handler(self, mock_handler):
        """Mock signal handler"""
        article = Article.objects.create(title='Test')

        # Handler should have been called
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        self.assertEqual(call_args[1]['instance'], article)

    def test_without_signal(self):
        """Disable signal for test"""
        # Disconnect signal
        post_save.disconnect(post_save_handler, sender=Article)

        try:
            article = Article.objects.create(title='Test')
            # Handler not called
        finally:
            # Reconnect signal
            post_save.connect(post_save_handler, sender=Article)
```

### Mock Celery Tasks

```python
@patch('myapp.tasks.send_notification.delay')
def test_async_notification(self, mock_task):
    """Mock Celery task"""
    article = Article.objects.create(title='Test')

    # Trigger task
    notify_subscribers(article)

    # Verify task was queued
    mock_task.assert_called_once_with(article.id)

@patch('myapp.tasks.send_notification.apply_async')
def test_scheduled_task(self, mock_apply_async):
    """Mock scheduled Celery task"""
    from datetime import timedelta
    from django.utils import timezone

    eta = timezone.now() + timedelta(hours=1)
    schedule_notification(article_id=1, eta=eta)

    mock_apply_async.assert_called_once_with(
        args=[1],
        eta=eta
    )
```

## Mock Time and Dates

### Mock timezone.now()

```python
from unittest.mock import patch
from django.utils import timezone
from datetime import datetime, timezone as tz

class TimeTests(TestCase):
    @patch('django.utils.timezone.now')
    def test_time_dependent_behavior(self, mock_now):
        """Mock current time"""
        # Set fixed time
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tz.utc)
        mock_now.return_value = fixed_time

        # Create article (will use mocked time)
        article = Article.objects.create(title='Test')

        # Verify timestamp
        self.assertEqual(article.created_at, fixed_time)

    @patch('django.utils.timezone.now')
    def test_expired_content(self, mock_now):
        """Test content expiration"""
        # Create article with expiration date
        expiry_date = datetime(2024, 6, 1, tzinfo=tz.utc)
        article = Article.objects.create(
            title='Test',
            expires_at=expiry_date
        )

        # Test before expiration
        mock_now.return_value = datetime(2024, 5, 1, tzinfo=tz.utc)
        self.assertFalse(article.is_expired())

        # Test after expiration
        mock_now.return_value = datetime(2024, 7, 1, tzinfo=tz.utc)
        self.assertTrue(article.is_expired())
```

### Mock datetime.now()

```python
@patch('myapp.utils.datetime')
def test_business_hours(self, mock_datetime):
    """Mock datetime for business hours logic"""
    # Monday at 2 PM
    mock_datetime.now.return_value = datetime(2024, 1, 15, 14, 0, 0)
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

    self.assertTrue(is_business_hours())

    # Saturday at 2 PM
    mock_datetime.now.return_value = datetime(2024, 1, 20, 14, 0, 0)
    self.assertFalse(is_business_hours())
```

### Using freezegun Library

```python
from freezegun import freeze_time
from django.utils import timezone

class FreezeTimeTests(TestCase):
    @freeze_time("2024-01-15 12:00:00")
    def test_with_frozen_time(self):
        """Use freezegun for cleaner time mocking"""
        article = Article.objects.create(title='Test')

        expected_time = timezone.datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(article.created_at, expected_time)

    def test_time_travel(self):
        """Test time progression"""
        with freeze_time("2024-01-01") as frozen_time:
            article = Article.objects.create(title='Test')

            # Fast forward 10 days
            frozen_time.tick(delta=timedelta(days=10))

            # Now it's Jan 11
            self.assertEqual(article.days_since_creation(), 10)
```

## Mock File Operations

### Mock File Uploads

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

class FileUploadTests(TestCase):
    def test_image_upload(self):
        """Create mock uploaded file"""
        # Create fake image file
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )

        # Create article with image
        article = Article.objects.create(
            title='Test',
            featured_image=image
        )

        # Verify upload
        self.assertTrue(article.featured_image)
        self.assertIn('test_image', article.featured_image.name)

        # Clean up
        article.featured_image.delete()

    def test_csv_import(self):
        """Mock CSV file upload"""
        csv_content = b'name,email\nJohn,john@example.com\nJane,jane@example.com'
        csv_file = SimpleUploadedFile(
            name='users.csv',
            content=csv_content,
            content_type='text/csv'
        )

        # Import users from CSV
        result = import_users(csv_file)

        self.assertEqual(result.created_count, 2)
        self.assertEqual(User.objects.count(), 2)
```

### Mock File System Operations

```python
from unittest.mock import patch, mock_open

@patch('builtins.open', new_callable=mock_open, read_data='file contents')
def test_read_config_file(self, mock_file):
    """Mock file reading"""
    config = read_config('config.txt')

    # Verify file was opened
    mock_file.assert_called_once_with('config.txt', 'r')

    # Verify content
    self.assertEqual(config, 'file contents')

@patch('builtins.open', new_callable=mock_open)
def test_write_log_file(self, mock_file):
    """Mock file writing"""
    write_log('test.log', 'Log entry')

    # Verify file was opened for writing
    mock_file.assert_called_once_with('test.log', 'a')

    # Verify write was called
    mock_file().write.assert_called_once_with('Log entry\n')

@patch('os.path.exists')
@patch('os.makedirs')
def test_create_directory(self, mock_makedirs, mock_exists):
    """Mock directory operations"""
    mock_exists.return_value = False

    ensure_directory('/path/to/dir')

    mock_exists.assert_called_once_with('/path/to/dir')
    mock_makedirs.assert_called_once_with('/path/to/dir')
```

## Advanced Patterns

### Mock Class Instances

```python
@patch('myapp.services.APIClient')
def test_api_client_instance(self, MockAPIClient):
    """Mock class and its instances"""
    # Configure mock instance
    mock_instance = MockAPIClient.return_value
    mock_instance.get_data.return_value = {'status': 'ok'}
    mock_instance.is_connected.return_value = True

    # Use the class (creates mock instance)
    service = MyService()
    result = service.fetch_data()

    # Verify instance methods were called
    mock_instance.connect.assert_called_once()
    mock_instance.get_data.assert_called_once_with(params={'limit': 10})

    # Verify result
    self.assertEqual(result['status'], 'ok')
```

### Mock Properties

```python
from unittest.mock import PropertyMock

@patch('myapp.models.Article.view_count', new_callable=PropertyMock)
def test_article_property(self, mock_view_count):
    """Mock model property"""
    mock_view_count.return_value = 1000

    article = Article.objects.create(title='Test')

    # Property returns mocked value
    self.assertEqual(article.view_count, 1000)
```

### Side Effects

```python
@patch('myapp.services.external_api_call')
def test_api_with_side_effects(self, mock_api):
    """Mock with different return values per call"""
    # Return different values on each call
    mock_api.side_effect = [
        {'status': 'pending'},  # First call
        {'status': 'processing'},  # Second call
        {'status': 'complete'}  # Third call
    ]

    # Poll until complete
    status = poll_until_complete()

    self.assertEqual(status, 'complete')
    self.assertEqual(mock_api.call_count, 3)

@patch('myapp.services.risky_operation')
def test_exception_side_effect(self, mock_operation):
    """Mock raises exception"""
    mock_operation.side_effect = ValueError('Invalid input')

    with self.assertRaises(ValueError):
        perform_operation()

@patch('myapp.services.random.choice')
def test_randomness_control(self, mock_choice):
    """Control randomness in tests"""
    # Make "random" choice predictable
    mock_choice.return_value = 'expected_value'

    result = function_with_random_choice()

    self.assertEqual(result, 'expected_value')
```

### Partial Mocking with wraps

```python
@patch('myapp.services.calculate_total', wraps=calculate_total)
def test_spy_on_function(self, mock_calculate):
    """Spy on real function (calls real implementation but tracks calls)"""
    result = process_order(items=[10, 20, 30])

    # Real function was called
    mock_calculate.assert_called_once_with([10, 20, 30])

    # Real result returned
    self.assertEqual(result, 60)
```

### Mock Context Managers

```python
from unittest.mock import MagicMock

@patch('myapp.services.DatabaseConnection')
def test_context_manager(self, MockConnection):
    """Mock context manager (with statement)"""
    # Configure mock context manager
    mock_conn = MagicMock()
    MockConnection.return_value.__enter__.return_value = mock_conn

    # Use context manager
    with DatabaseConnection() as conn:
        conn.execute('SELECT * FROM users')

    # Verify
    mock_conn.execute.assert_called_once_with('SELECT * FROM users')
```

## Best Practices

### 1. Patch at the Right Level

```python
# ❌ BAD: Patching too high up
@patch('requests.get')  # Affects ALL requests in ALL modules
def test_my_function(self, mock_get):
    pass

# ✅ GOOD: Patch where it's used
@patch('myapp.services.requests.get')  # Only affects this module
def test_my_function(self, mock_get):
    pass
```

### 2. Don't Mock What You Don't Own (Usually)

```python
# ❌ BAD: Mocking Django ORM (tests nothing)
@patch('myapp.models.Article.objects.create')
def test_article_creation(self, mock_create):
    # This doesn't test your code!
    pass

# ✅ GOOD: Test real database operations
def test_article_creation(self):
    article = Article.objects.create(title='Test')
    self.assertEqual(article.title, 'Test')
```

### 3. Use Specific Assertions

```python
@patch('myapp.services.send_email')
def test_notification(self, mock_send):
    notify_user('user@example.com', 'Hello')

    # ❌ BAD: Just checking it was called
    mock_send.assert_called()

    # ✅ GOOD: Verify exact arguments
    mock_send.assert_called_once_with(
        to='user@example.com',
        subject='Notification',
        body='Hello'
    )
```

### 4. Reset Mocks Between Tests

```python
class MyTests(TestCase):
    def setUp(self):
        self.patcher = patch('myapp.services.external_api')
        self.mock_api = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_one(self):
        # Mock is fresh for this test
        self.mock_api.return_value = 'result1'
        # ...

    def test_two(self):
        # Mock is fresh for this test too
        self.mock_api.return_value = 'result2'
        # ...
```

### 5. Don't Over-Mock

```python
# ❌ BAD: Mocking everything (tests nothing real)
@patch('myapp.services.function_a')
@patch('myapp.services.function_b')
@patch('myapp.services.function_c')
def test_workflow(self, mock_c, mock_b, mock_a):
    # This test is too isolated from reality
    pass

# ✅ GOOD: Only mock external dependencies
@patch('myapp.services.external_api_call')
def test_workflow(self, mock_api):
    # Rest of the code runs normally
    pass
```

### 6. Use descriptive mock names

```python
# ❌ BAD
@patch('myapp.services.x')
@patch('myapp.services.y')
def test_something(self, m1, m2):
    pass

# ✅ GOOD
@patch('myapp.services.send_email')
@patch('myapp.services.send_sms')
def test_notification(self, mock_send_sms, mock_send_email):
    pass
```

## Common Pitfalls

### Pitfall 1: Wrong Patch Target

```python
# module.py
from datetime import datetime

def get_timestamp():
    return datetime.now()

# ❌ WRONG
@patch('datetime.datetime.now')  # Won't work!
def test_timestamp(self, mock_now):
    pass

# ✅ CORRECT
@patch('module.datetime.now')  # Patch where it's imported
def test_timestamp(self, mock_now):
    pass
```

### Pitfall 2: Forgetting return_value

```python
@patch('myapp.services.get_data')
def test_data_processing(self, mock_get_data):
    # ❌ WRONG: Mock returns Mock object by default
    result = process_data()
    # result is a Mock, not actual data!

    # ✅ CORRECT: Set return value
    mock_get_data.return_value = {'key': 'value'}
    result = process_data()
    # Now result is {'key': 'value'}
```

### Pitfall 3: Not Checking Mock Calls

```python
@patch('myapp.services.send_notification')
def test_notification(self, mock_send):
    notify_user('user@example.com')

    # ❌ BAD: Not verifying anything
    pass

    # ✅ GOOD: Verify mock was used correctly
    mock_send.assert_called_once_with('user@example.com')
```

## Summary

**Key Takeaways:**
- Mock external dependencies (APIs, emails, files)
- Patch where objects are USED, not defined
- Use specific assertions (`assert_called_once_with`)
- Don't over-mock (test real code when possible)
- Reset mocks between tests
- Use descriptive names for mocks

**Most Common Patterns:**
- `@patch('module.function')` - Mock functions
- `mock.return_value` - Set return value
- `mock.side_effect` - Multiple returns or exceptions
- `mock.assert_called_once_with()` - Verify calls
- `@freeze_time()` - Mock time (with freezegun)

**Remember:** Mocks make tests faster and more reliable, but too much mocking can make tests meaningless!
