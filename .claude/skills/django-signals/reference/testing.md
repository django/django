# Testing Django Signals

Comprehensive guide to testing signal-driven behavior in Django applications.

## Table of Contents

- [Basic Testing Patterns](#basic-testing-patterns)
- [Testing Signal Handlers](#testing-signal-handlers)
- [Testing Signal Sending](#testing-signal-sending)
- [Mocking Signals](#mocking-signals)
- [Testing Custom Signals](#testing-custom-signals)
- [Integration Testing](#integration-testing)
- [Performance Testing](#performance-testing)
- [Common Testing Pitfalls](#common-testing-pitfalls)

## Basic Testing Patterns

### Testing That a Signal Is Sent

```python
from django.test import TestCase
from django.db.models.signals import post_save
from myapp.models import Article

class ArticleSignalTests(TestCase):
    def test_post_save_signal_sent_on_create(self):
        """Test that post_save signal is sent when Article is created."""
        signal_received = []

        def receiver(sender, instance, created, **kwargs):
            signal_received.append({
                'sender': sender,
                'instance': instance,
                'created': created
            })

        # Connect test receiver
        post_save.connect(receiver, sender=Article)

        try:
            # Create article
            article = Article.objects.create(title='Test')

            # Verify signal was sent
            self.assertEqual(len(signal_received), 1)
            self.assertEqual(signal_received[0]['sender'], Article)
            self.assertEqual(signal_received[0]['instance'], article)
            self.assertTrue(signal_received[0]['created'])
        finally:
            # Clean up
            post_save.disconnect(receiver, sender=Article)
```

### Testing Signal Handler Side Effects

```python
from django.test import TestCase
from django.core import mail
from myapp.models import Order

class OrderSignalTests(TestCase):
    def test_confirmation_email_sent(self):
        """Test that confirmation email is sent when order is created."""
        order = Order.objects.create(
            customer_email='test@example.com',
            total=100
        )

        # Verify email was sent by signal handler
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('Order Confirmation', mail.outbox[0].subject)

    def test_cache_updated(self):
        """Test that cache is updated when order is saved."""
        from django.core.cache import cache

        order = Order.objects.create(total=100)
        order.status = 'confirmed'
        order.save()

        # Verify cache was updated by signal handler
        cached_order = cache.get(f'order_{order.pk}')
        self.assertIsNotNone(cached_order)
        self.assertEqual(cached_order.status, 'confirmed')
```

### Context Manager for Signal Testing

```python
from contextlib import contextmanager
from django.db.models.signals import post_save

@contextmanager
def capture_signal(signal, sender=None):
    """Context manager to capture signal calls."""
    captured = []

    def receiver(sender, **kwargs):
        captured.append({'sender': sender, 'kwargs': kwargs})

    signal.connect(receiver, sender=sender)
    try:
        yield captured
    finally:
        signal.disconnect(receiver, sender=sender)

# Usage
class ArticleTests(TestCase):
    def test_article_saved_signal(self):
        """Test article save sends signal."""
        with capture_signal(post_save, sender=Article) as captured:
            article = Article.objects.create(title='Test')

            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0]['sender'], Article)
            self.assertTrue(captured[0]['kwargs']['created'])
            self.assertEqual(captured[0]['kwargs']['instance'], article)
```

## Testing Signal Handlers

### Testing Handler Logic

```python
from django.test import TestCase
from myapp.signals import article_post_save_handler
from myapp.models import Article

class ArticleHandlerTests(TestCase):
    def test_handler_sends_notification_for_new_article(self):
        """Test handler sends notification for new articles."""
        from django.core import mail

        article = Article.objects.create(title='Test')

        # Call handler directly
        article_post_save_handler(
            sender=Article,
            instance=article,
            created=True
        )

        # Verify notification sent
        self.assertEqual(len(mail.outbox), 1)

    def test_handler_skips_notification_for_updates(self):
        """Test handler doesn't send notification for updates."""
        from django.core import mail

        article = Article.objects.create(title='Test')
        mail.outbox.clear()  # Clear creation email

        # Call handler with created=False
        article_post_save_handler(
            sender=Article,
            instance=article,
            created=False
        )

        # Verify no notification sent
        self.assertEqual(len(mail.outbox), 0)

    def test_handler_with_error(self):
        """Test handler error handling."""
        article = Article.objects.create(title='Test')

        # Mock an error in notification
        with patch('myapp.signals.send_notification') as mock_send:
            mock_send.side_effect = Exception("Email service down")

            # Handler should not raise exception
            try:
                article_post_save_handler(
                    sender=Article,
                    instance=article,
                    created=True
                )
            except Exception as e:
                self.fail(f"Handler raised exception: {e}")
```

### Testing Handler with Database Operations

```python
from django.test import TestCase, TransactionTestCase
from django.db import transaction

class OrderHandlerTests(TransactionTestCase):
    """Use TransactionTestCase for handlers that use on_commit()."""

    def test_handler_uses_on_commit(self):
        """Test handler waits for transaction commit."""
        from django.core import mail

        with transaction.atomic():
            order = Order.objects.create(total=100)
            # Email not sent yet (handler uses on_commit)
            self.assertEqual(len(mail.outbox), 0)

        # After transaction commits, email should be sent
        self.assertEqual(len(mail.outbox), 1)

    def test_handler_not_called_on_rollback(self):
        """Test handler not called if transaction rolls back."""
        from django.core import mail

        try:
            with transaction.atomic():
                order = Order.objects.create(total=100)
                raise Exception("Force rollback")
        except Exception:
            pass

        # Handler should not have run (transaction rolled back)
        self.assertEqual(len(mail.outbox), 0)
```

### Testing Handler Performance

```python
from django.test import TestCase
from django.test.utils import override_settings
import time

class HandlerPerformanceTests(TestCase):
    def test_handler_execution_time(self):
        """Test that handler executes quickly."""
        start_time = time.time()

        # Create 100 articles
        for i in range(100):
            Article.objects.create(title=f'Article {i}')

        elapsed = time.time() - start_time

        # Handler should be fast (adjust threshold as needed)
        self.assertLess(elapsed, 1.0, f"Handler too slow: {elapsed:.2f}s")

    def test_handler_database_queries(self):
        """Test that handler doesn't cause N+1 queries."""
        with self.assertNumQueries(1):  # Only the create query
            article = Article.objects.create(title='Test')
```

## Testing Signal Sending

### Testing That Code Sends Signals

```python
from django.test import TestCase
from unittest.mock import patch
from myapp.services import process_payment
from myapp.signals import payment_completed

class PaymentServiceTests(TestCase):
    @patch.object(payment_completed, 'send')
    def test_process_payment_sends_signal(self, mock_signal):
        """Test that process_payment sends payment_completed signal."""
        order = Order.objects.create(total=100)

        payment = process_payment(order, 100, 'tok_test')

        # Verify signal was sent
        mock_signal.assert_called_once()

        # Verify signal arguments
        call_kwargs = mock_signal.call_args[1]
        self.assertEqual(call_kwargs['sender'], Payment)
        self.assertEqual(call_kwargs['payment'], payment)
        self.assertEqual(call_kwargs['amount'], 100)

    @patch.object(payment_completed, 'send')
    def test_signal_not_sent_on_error(self, mock_signal):
        """Test signal not sent if payment fails."""
        order = Order.objects.create(total=100)

        with self.assertRaises(PaymentError):
            process_payment(order, 100, 'invalid_token')

        # Signal should not have been sent
        mock_signal.assert_not_called()
```

### Testing Signal Arguments

```python
class SignalArgumentTests(TestCase):
    def test_signal_includes_all_required_arguments(self):
        """Test signal is sent with all required arguments."""
        received_args = []

        def receiver(sender, payment, amount, transaction_id, **kwargs):
            received_args.append({
                'sender': sender,
                'payment': payment,
                'amount': amount,
                'transaction_id': transaction_id,
                'kwargs': kwargs
            })

        payment_completed.connect(receiver)

        try:
            order = Order.objects.create(total=100)
            process_payment(order, 100, 'tok_test')

            # Verify all arguments present
            self.assertEqual(len(received_args), 1)
            args = received_args[0]

            self.assertEqual(args['sender'], Payment)
            self.assertIsInstance(args['payment'], Payment)
            self.assertEqual(args['amount'], 100)
            self.assertIsInstance(args['transaction_id'], str)
            self.assertIn('customer', args['kwargs'])
        finally:
            payment_completed.disconnect(receiver)
```

## Mocking Signals

### Disabling Signal Handlers in Tests

```python
from django.test import TestCase
from django.db.models.signals import post_save
from myapp.models import Article
from myapp.signals import article_post_save_handler

class ArticleTests(TestCase):
    def test_create_article_without_signal(self):
        """Test creating article without triggering signal handler."""

        # Disconnect signal
        post_save.disconnect(article_post_save_handler, sender=Article)

        try:
            # Create article (handler won't run)
            article = Article.objects.create(title='Test')

            # Verify handler side effects didn't occur
            from django.core import mail
            self.assertEqual(len(mail.outbox), 0)
        finally:
            # Reconnect signal
            post_save.connect(article_post_save_handler, sender=Article)
```

### Context Manager for Disabling Signals

```python
from contextlib import contextmanager

@contextmanager
def disable_signal(signal, receiver, sender):
    """Temporarily disable a signal handler."""
    signal.disconnect(receiver, sender=sender)
    try:
        yield
    finally:
        signal.connect(receiver, sender=sender)

# Usage
class ArticleTests(TestCase):
    def test_without_signal_handler(self):
        """Test article creation without signal handler."""
        from myapp.signals import article_post_save_handler

        with disable_signal(post_save, article_post_save_handler, Article):
            article = Article.objects.create(title='Test')
            # Handler won't run
```

### Mocking with unittest.mock

```python
from unittest.mock import patch

class ArticleTests(TestCase):
    @patch('myapp.signals.send_notification')
    def test_with_mocked_handler_dependency(self, mock_send):
        """Test with mocked signal handler dependency."""

        # Create article (signal handler will call mock)
        article = Article.objects.create(title='Test')

        # Verify mock was called
        mock_send.assert_called_once_with(article)

    @patch('myapp.signals.article_post_save_handler')
    def test_with_mocked_handler(self, mock_handler):
        """Test with entire handler mocked."""

        article = Article.objects.create(title='Test')

        # Verify handler was called
        mock_handler.assert_called_once()
        call_kwargs = mock_handler.call_args[1]
        self.assertEqual(call_kwargs['instance'], article)
```

### Factory for Signal-Free Model Creation

```python
from django.db.models.signals import post_save, pre_save

@contextmanager
def without_signals():
    """Context manager to disable all model signals."""
    signals = [
        (post_save, 'post_save'),
        (pre_save, 'pre_save'),
        # Add other signals as needed
    ]

    # Store original receivers
    original_receivers = {}
    for signal, name in signals:
        original_receivers[name] = signal.receivers
        signal.receivers = []

    try:
        yield
    finally:
        # Restore receivers
        for signal, name in signals:
            signal.receivers = original_receivers[name]

# Usage
def create_article_without_signals(**kwargs):
    """Create article without triggering signals."""
    with without_signals():
        return Article.objects.create(**kwargs)

class ArticleTests(TestCase):
    def test_bulk_creation(self):
        """Test bulk article creation without signal overhead."""
        # Create 1000 articles without signals
        articles = []
        with without_signals():
            for i in range(1000):
                articles.append(Article.objects.create(title=f'Article {i}'))

        self.assertEqual(len(articles), 1000)
```

## Testing Custom Signals

### Testing Signal Definition

```python
from django.test import SimpleTestCase
from myapp.signals import payment_completed

class CustomSignalTests(SimpleTestCase):
    def test_signal_exists(self):
        """Test that custom signal is defined."""
        from django.dispatch import Signal
        self.assertIsInstance(payment_completed, Signal)

    def test_signal_documented(self):
        """Test that signal has documentation."""
        self.assertIsNotNone(payment_completed.__doc__)
        self.assertIn('payment', payment_completed.__doc__.lower())
```

### Testing Custom Signal Sending

```python
class CustomSignalSendingTests(TestCase):
    def test_custom_signal_sent(self):
        """Test that custom signal is sent correctly."""
        from myapp.signals import payment_completed

        received = []

        def receiver(sender, payment, amount, **kwargs):
            received.append({
                'sender': sender,
                'payment': payment,
                'amount': amount
            })

        payment_completed.connect(receiver)

        try:
            # Trigger code that should send signal
            from myapp.services import process_payment
            order = Order.objects.create(total=100)
            payment = process_payment(order, 100, 'tok_test')

            # Verify signal sent
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]['payment'], payment)
        finally:
            payment_completed.disconnect(receiver)

    def test_custom_signal_with_multiple_receivers(self):
        """Test custom signal with multiple receivers."""
        received_1 = []
        received_2 = []

        def receiver_1(sender, **kwargs):
            received_1.append(kwargs)

        def receiver_2(sender, **kwargs):
            received_2.append(kwargs)

        payment_completed.connect(receiver_1)
        payment_completed.connect(receiver_2)

        try:
            order = Order.objects.create(total=100)
            process_payment(order, 100, 'tok_test')

            # Both receivers should have been called
            self.assertEqual(len(received_1), 1)
            self.assertEqual(len(received_2), 1)
        finally:
            payment_completed.disconnect(receiver_1)
            payment_completed.disconnect(receiver_2)
```

## Integration Testing

### Testing End-to-End Signal Flow

```python
from django.test import TestCase, TransactionTestCase

class OrderWorkflowTests(TransactionTestCase):
    """Test complete order workflow with signals."""

    def test_complete_order_workflow(self):
        """Test entire order flow with all signals."""
        from django.core import mail
        from django.core.cache import cache

        # Create order (triggers post_save signal)
        order = Order.objects.create(
            customer_email='test@example.com',
            total=100
        )

        # Verify order creation effects
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Order Confirmation', mail.outbox[0].subject)

        # Confirm order (triggers custom signal)
        order.status = 'confirmed'
        order.save()

        # Verify confirmation effects
        self.assertEqual(len(mail.outbox), 2)
        cached_order = cache.get(f'order_{order.pk}')
        self.assertIsNotNone(cached_order)

        # Ship order (triggers another signal)
        order.status = 'shipped'
        order.tracking_number = '123456'
        order.save()

        # Verify shipping effects
        self.assertEqual(len(mail.outbox), 3)
        self.assertIn('shipped', mail.outbox[2].subject.lower())
```

### Testing Signal Chains

```python
class SignalChainTests(TestCase):
    """Test signals that trigger other signals."""

    def test_payment_triggers_order_confirmation(self):
        """Test payment signal triggers order confirmation signal."""
        order_confirmed_called = []
        payment_completed_called = []

        def payment_receiver(sender, **kwargs):
            payment_completed_called.append(kwargs)

        def order_receiver(sender, **kwargs):
            order_confirmed_called.append(kwargs)

        from myapp.signals import payment_completed, order_confirmed

        payment_completed.connect(payment_receiver)
        order_confirmed.connect(order_receiver)

        try:
            # Process payment (should trigger both signals)
            order = Order.objects.create(total=100)
            process_payment(order, 100, 'tok_test')

            # Verify both signals fired
            self.assertEqual(len(payment_completed_called), 1)
            self.assertEqual(len(order_confirmed_called), 1)
        finally:
            payment_completed.disconnect(payment_receiver)
            order_confirmed.disconnect(order_receiver)
```

## Performance Testing

### Testing Signal Overhead

```python
from django.test import TestCase
import time

class SignalPerformanceTests(TestCase):
    def test_signal_overhead(self):
        """Measure signal overhead."""

        # Create without signals
        from myapp.models import Article
        from django.db.models.signals import post_save
        from myapp.signals import article_post_save_handler

        post_save.disconnect(article_post_save_handler, sender=Article)

        start = time.time()
        for i in range(100):
            Article.objects.create(title=f'Article {i}')
        time_without = time.time() - start

        post_save.connect(article_post_save_handler, sender=Article)

        # Clear database
        Article.objects.all().delete()

        # Create with signals
        start = time.time()
        for i in range(100):
            Article.objects.create(title=f'Article {i}')
        time_with = time.time() - start

        # Calculate overhead
        overhead = time_with - time_without
        overhead_pct = (overhead / time_without) * 100

        print(f"Without signals: {time_without:.2f}s")
        print(f"With signals: {time_with:.2f}s")
        print(f"Overhead: {overhead:.2f}s ({overhead_pct:.1f}%)")

        # Verify overhead is acceptable (adjust threshold)
        self.assertLess(overhead_pct, 50, "Signal overhead too high")
```

### Testing Signal Handler Query Count

```python
class SignalQueryTests(TestCase):
    def test_handler_query_count(self):
        """Test number of queries in signal handler."""

        # Use assertNumQueries to verify query count
        with self.assertNumQueries(2):  # create + handler queries
            Article.objects.create(title='Test')

    def test_handler_no_n_plus_one(self):
        """Test handler doesn't cause N+1 queries."""

        # Create related data
        category = Category.objects.create(name='Tech')

        # Should be constant queries regardless of count
        with self.assertNumQueries(2):
            Article.objects.create(title='Article 1', category=category)

        with self.assertNumQueries(2):
            Article.objects.create(title='Article 2', category=category)
```

## Common Testing Pitfalls

### Pitfall 1: Not Cleaning Up Signal Connections

```python
# BAD: Signal remains connected after test
class BadTests(TestCase):
    def test_signal(self):
        def receiver(sender, **kwargs):
            pass

        post_save.connect(receiver, sender=Article)
        # Forgot to disconnect!

# GOOD: Always disconnect
class GoodTests(TestCase):
    def test_signal(self):
        def receiver(sender, **kwargs):
            pass

        post_save.connect(receiver, sender=Article)
        try:
            # Test code
            pass
        finally:
            post_save.disconnect(receiver, sender=Article)
```

### Pitfall 2: Wrong Test Class for on_commit()

```python
# BAD: TestCase doesn't work with on_commit()
class BadTests(TestCase):
    def test_handler_with_on_commit(self):
        order = Order.objects.create(total=100)
        # Handler uses on_commit() but won't fire in TestCase!

# GOOD: Use TransactionTestCase
class GoodTests(TransactionTestCase):
    def test_handler_with_on_commit(self):
        order = Order.objects.create(total=100)
        # Handler fires correctly
```

### Pitfall 3: Testing Implementation Instead of Behavior

```python
# BAD: Testing that signal is sent (implementation detail)
class BadTests(TestCase):
    def test_post_save_signal_sent(self):
        with capture_signal(post_save, sender=Article) as captured:
            Article.objects.create(title='Test')
            self.assertEqual(len(captured), 1)

# GOOD: Testing the actual behavior/side effects
class GoodTests(TestCase):
    def test_notification_sent_when_article_created(self):
        Article.objects.create(title='Test')
        self.assertEqual(len(mail.outbox), 1)
```

### Pitfall 4: Not Isolating Signal Tests

```python
# BAD: Tests affect each other
class BadTests(TestCase):
    def test_1(self):
        Article.objects.create(title='Test 1')
        # Leaves data in database

    def test_2(self):
        # Affected by test_1's data
        self.assertEqual(Article.objects.count(), 0)  # FAILS!

# GOOD: Each test is isolated
class GoodTests(TestCase):
    def setUp(self):
        # Clean state for each test
        Article.objects.all().delete()

    def test_1(self):
        Article.objects.create(title='Test 1')
        self.assertEqual(Article.objects.count(), 1)

    def test_2(self):
        # Fresh state
        self.assertEqual(Article.objects.count(), 0)
```

### Pitfall 5: Not Testing Error Conditions

```python
# BAD: Only testing happy path
class BadTests(TestCase):
    def test_handler(self):
        article = Article.objects.create(title='Test')
        # Only tests when everything works

# GOOD: Test error conditions
class GoodTests(TestCase):
    def test_handler_with_email_error(self):
        """Test handler when email service fails."""
        with patch('myapp.signals.send_email') as mock_send:
            mock_send.side_effect = EmailError("Service down")

            # Handler should not crash
            article = Article.objects.create(title='Test')

            # Verify error was logged
            # Verify alternative action was taken
```

## Testing Checklist

- [ ] Test that signals are sent when expected
- [ ] Test that signals are NOT sent when not expected
- [ ] Test all signal handler side effects
- [ ] Test signal handler error handling
- [ ] Test with and without transactions (on_commit)
- [ ] Test signal handler performance
- [ ] Test signal handler query count
- [ ] Test custom signal arguments
- [ ] Clean up signal connections after tests
- [ ] Use appropriate test class (TestCase vs TransactionTestCase)
- [ ] Test error conditions, not just happy path
- [ ] Test behavior, not implementation details
