# Testing Management Commands

This reference covers comprehensive testing strategies for Django management commands.

## Table of Contents
- [Basic Testing](#basic-testing)
- [Testing Output](#testing-output)
- [Testing Arguments](#testing-arguments)
- [Testing Database Operations](#testing-database-operations)
- [Testing Error Conditions](#testing-error-conditions)
- [Advanced Testing Patterns](#advanced-testing-patterns)

## Basic Testing

### Simple Command Test

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestMyCommand(TestCase):
    def test_command_runs_successfully(self):
        """Test command executes without errors"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        self.assertIn('Success', out.getvalue())
```

### Testing with Arguments

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestMyCommand(TestCase):
    def test_command_with_positional_args(self):
        """Test command with positional arguments"""
        out = StringIO()
        call_command('mycommand', 'arg1', 'arg2', stdout=out)
        self.assertIn('Processed arg1 and arg2', out.getvalue())

    def test_command_with_optional_args(self):
        """Test command with optional arguments"""
        out = StringIO()
        call_command('mycommand', '--verbose', '--limit=100', stdout=out)
        output = out.getvalue()
        self.assertIn('verbose mode', output.lower())
```

### Testing Exit Codes

```python
from django.core.management import call_command, CommandError
from django.test import TestCase

class TestMyCommand(TestCase):
    def test_command_fails_with_invalid_input(self):
        """Test command raises CommandError on invalid input"""
        with self.assertRaises(CommandError):
            call_command('mycommand', '--invalid-option')

    def test_command_error_message(self):
        """Test specific error message"""
        with self.assertRaisesMessage(CommandError, 'File not found'):
            call_command('mycommand', 'nonexistent.txt')
```

## Testing Output

### Capturing stdout and stderr

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestOutputCommand(TestCase):
    def test_success_message(self):
        """Test success output"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        self.assertIn('Successfully processed', out.getvalue())

    def test_error_output(self):
        """Test error messages go to stderr"""
        out = StringIO()
        err = StringIO()
        call_command('mycommand', '--trigger-warning',
                    stdout=out, stderr=err)
        self.assertIn('Warning', err.getvalue())
        self.assertEqual('', out.getvalue())

    def test_verbose_output(self):
        """Test verbosity levels"""
        # Verbosity 0 (quiet)
        out = StringIO()
        call_command('mycommand', verbosity=0, stdout=out)
        self.assertEqual('', out.getvalue())

        # Verbosity 2 (verbose)
        out = StringIO()
        call_command('mycommand', verbosity=2, stdout=out)
        output = out.getvalue()
        self.assertIn('Detailed information', output)
```

### Testing Styled Output

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestStyledOutput(TestCase):
    def test_colored_output(self):
        """Test output contains style codes"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        output = out.getvalue()

        # Output should contain ANSI color codes
        # (when not using --no-color)
        self.assertTrue(output)

    def test_no_color_option(self):
        """Test --no-color removes styling"""
        out = StringIO()
        call_command('mycommand', '--no-color', stdout=out)
        output = out.getvalue()

        # Should not contain ANSI escape codes
        self.assertNotIn('\033[', output)
```

### Testing Multi-Line Output

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestMultiLineOutput(TestCase):
    def test_progress_messages(self):
        """Test multiple progress messages"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        output = out.getvalue()
        lines = output.strip().split('\n')

        self.assertGreaterEqual(len(lines), 3)
        self.assertIn('Started', lines[0])
        self.assertIn('Processing', lines[1])
        self.assertIn('Complete', lines[-1])

    def test_summary_output(self):
        """Test summary statistics"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        output = out.getvalue()

        self.assertIn('Total: 100', output)
        self.assertIn('Success: 95', output)
        self.assertIn('Errors: 5', output)
```

## Testing Arguments

### Testing Required Arguments

```python
from django.core.management import call_command, CommandError
from django.test import TestCase
import sys

class TestCommandArguments(TestCase):
    def test_missing_required_argument(self):
        """Test command fails without required argument"""
        with self.assertRaises(SystemExit):
            # SystemExit is raised by argparse for missing args
            call_command('mycommand')

    def test_required_argument_provided(self):
        """Test command succeeds with required argument"""
        out = StringIO()
        call_command('mycommand', 'required_value', stdout=out)
        self.assertIn('Processed required_value', out.getvalue())
```

### Testing Optional Arguments

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestOptionalArguments(TestCase):
    def test_default_values(self):
        """Test command uses default values"""
        out = StringIO()
        call_command('mycommand', stdout=out)
        self.assertIn('limit: 100', out.getvalue())  # default limit

    def test_custom_values(self):
        """Test command uses provided values"""
        out = StringIO()
        call_command('mycommand', '--limit=500', stdout=out)
        self.assertIn('limit: 500', out.getvalue())

    def test_boolean_flags(self):
        """Test boolean flag arguments"""
        out = StringIO()

        # Without flag
        call_command('mycommand', stdout=out)
        self.assertNotIn('verbose mode', out.getvalue())

        # With flag
        out = StringIO()
        call_command('mycommand', '--verbose', stdout=out)
        self.assertIn('verbose mode', out.getvalue())
```

### Testing Argument Validation

```python
from django.core.management import call_command, CommandError
from django.test import TestCase

class TestArgumentValidation(TestCase):
    def test_invalid_choice(self):
        """Test invalid choice argument"""
        with self.assertRaises(SystemExit):
            call_command('mycommand', '--format=invalid')

    def test_valid_choices(self):
        """Test all valid choices"""
        for format_type in ['json', 'csv', 'xml']:
            out = StringIO()
            call_command('mycommand', f'--format={format_type}', stdout=out)
            self.assertIn(f'Format: {format_type}', out.getvalue())

    def test_integer_validation(self):
        """Test integer argument validation"""
        with self.assertRaises(CommandError):
            call_command('mycommand', '--limit=-1')

        with self.assertRaises(CommandError):
            call_command('mycommand', '--limit=99999')

        # Valid range
        out = StringIO()
        call_command('mycommand', '--limit=100', stdout=out)
        self.assertIn('Success', out.getvalue())
```

## Testing Database Operations

### Testing Data Creation

```python
from django.core.management import call_command
from django.test import TestCase
from myapp.models import MyModel

class TestDatabaseOperations(TestCase):
    def test_creates_records(self):
        """Test command creates database records"""
        self.assertEqual(MyModel.objects.count(), 0)

        call_command('mycommand')

        self.assertGreater(MyModel.objects.count(), 0)

    def test_created_data_values(self):
        """Test created records have correct values"""
        call_command('mycommand', '--name=TestItem')

        obj = MyModel.objects.first()
        self.assertEqual(obj.name, 'TestItem')
        self.assertEqual(obj.status, 'active')
```

### Testing Data Updates

```python
from django.core.management import call_command
from django.test import TestCase
from myapp.models import MyModel

class TestUpdateOperations(TestCase):
    def setUp(self):
        """Create test data"""
        self.item1 = MyModel.objects.create(name='Item 1', status='pending')
        self.item2 = MyModel.objects.create(name='Item 2', status='pending')

    def test_updates_records(self):
        """Test command updates records"""
        call_command('mycommand', '--status=completed')

        self.item1.refresh_from_db()
        self.item2.refresh_from_db()

        self.assertEqual(self.item1.status, 'completed')
        self.assertEqual(self.item2.status, 'completed')

    def test_updates_count(self):
        """Test correct number of updates"""
        out = StringIO()
        call_command('mycommand', stdout=out)

        self.assertIn('Updated 2 records', out.getvalue())
```

### Testing Data Deletion

```python
from django.core.management import call_command
from django.test import TestCase
from myapp.models import MyModel

class TestDeleteOperations(TestCase):
    def setUp(self):
        """Create test data"""
        MyModel.objects.create(name='Keep', status='active')
        MyModel.objects.create(name='Delete 1', status='old')
        MyModel.objects.create(name='Delete 2', status='old')

    def test_deletes_correct_records(self):
        """Test only matching records are deleted"""
        self.assertEqual(MyModel.objects.count(), 3)

        call_command('mycommand', '--delete-old')

        self.assertEqual(MyModel.objects.count(), 1)
        self.assertEqual(MyModel.objects.first().name, 'Keep')

    def test_dry_run_mode(self):
        """Test dry-run doesn't delete records"""
        call_command('mycommand', '--delete-old', '--dry-run')

        # Nothing should be deleted
        self.assertEqual(MyModel.objects.count(), 3)
```

### Testing Transactions

```python
from django.core.management import call_command, CommandError
from django.test import TestCase
from myapp.models import MyModel

class TestTransactions(TestCase):
    def test_transaction_rollback_on_error(self):
        """Test transaction rolls back on error"""
        self.assertEqual(MyModel.objects.count(), 0)

        with self.assertRaises(CommandError):
            # Command should fail and rollback
            call_command('mycommand', '--trigger-error')

        # No records should be created
        self.assertEqual(MyModel.objects.count(), 0)

    def test_transaction_commit_on_success(self):
        """Test transaction commits on success"""
        call_command('mycommand')

        # All records should be committed
        self.assertGreater(MyModel.objects.count(), 0)
```

### Testing with TransactionTestCase

```python
from django.core.management import call_command
from django.test import TransactionTestCase
from myapp.models import MyModel

class TestCommandTransactions(TransactionTestCase):
    """Use TransactionTestCase for testing transaction behavior"""

    def test_autocommit_behavior(self):
        """Test operations in autocommit mode"""
        call_command('mycommand', '--no-transaction')

        # Records are committed immediately
        self.assertGreater(MyModel.objects.count(), 0)

    def test_atomic_behavior(self):
        """Test operations in atomic transaction"""
        with self.assertRaises(Exception):
            call_command('mycommand', '--atomic', '--fail-midway')

        # All operations should be rolled back
        self.assertEqual(MyModel.objects.count(), 0)
```

## Testing Error Conditions

### Testing CommandError

```python
from django.core.management import call_command, CommandError
from django.test import TestCase

class TestErrorHandling(TestCase):
    def test_missing_file_error(self):
        """Test error when file doesn't exist"""
        with self.assertRaises(CommandError) as cm:
            call_command('mycommand', 'nonexistent.txt')

        self.assertIn('File not found', str(cm.exception))

    def test_validation_error(self):
        """Test error on invalid data"""
        with self.assertRaises(CommandError) as cm:
            call_command('mycommand', '--invalid-data')

        self.assertIn('Validation failed', str(cm.exception))
```

### Testing Exception Handling

```python
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

class TestExceptionHandling(TestCase):
    @patch('myapp.management.commands.mycommand.external_api_call')
    def test_handles_api_failure(self, mock_api):
        """Test graceful handling of API failures"""
        mock_api.side_effect = Exception('API unavailable')

        err = StringIO()
        call_command('mycommand', stderr=err)

        error_output = err.getvalue()
        self.assertIn('API unavailable', error_output)

    def test_partial_failure_recovery(self):
        """Test command continues on recoverable errors"""
        out = StringIO()
        err = StringIO()

        call_command('mycommand', '--skip-errors',
                    stdout=out, stderr=err)

        # Should complete despite errors
        self.assertIn('Complete', out.getvalue())
        self.assertIn('Error', err.getvalue())
```

### Testing Edge Cases

```python
from django.core.management import call_command
from django.test import TestCase
from myapp.models import MyModel

class TestEdgeCases(TestCase):
    def test_empty_queryset(self):
        """Test command handles empty data gracefully"""
        self.assertEqual(MyModel.objects.count(), 0)

        out = StringIO()
        call_command('mycommand', stdout=out)

        self.assertIn('No records to process', out.getvalue())

    def test_large_dataset(self):
        """Test command handles large datasets"""
        # Create many records
        MyModel.objects.bulk_create([
            MyModel(name=f'Item {i}') for i in range(10000)
        ])

        out = StringIO()
        call_command('mycommand', stdout=out)

        self.assertIn('Processed 10000', out.getvalue())

    def test_unicode_handling(self):
        """Test command handles unicode correctly"""
        out = StringIO()
        call_command('mycommand', '--name=Test™®©', stdout=out)

        output = out.getvalue()
        self.assertIn('Test™®©', output)
```

## Advanced Testing Patterns

### Testing with Fixtures

```python
from django.core.management import call_command
from django.test import TestCase

class TestWithFixtures(TestCase):
    fixtures = ['test_data.json']

    def test_processes_fixture_data(self):
        """Test command processes fixture data correctly"""
        from myapp.models import MyModel

        initial_count = MyModel.objects.count()
        self.assertGreater(initial_count, 0)

        out = StringIO()
        call_command('mycommand', stdout=out)

        self.assertIn(f'Processed {initial_count}', out.getvalue())
```

### Testing with Mocks

```python
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch, MagicMock

class TestWithMocks(TestCase):
    @patch('myapp.management.commands.mycommand.requests.get')
    def test_api_call(self, mock_get):
        """Test command with mocked API call"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response

        out = StringIO()
        call_command('mycommand', stdout=out)

        mock_get.assert_called_once()
        self.assertIn('API response: ok', out.getvalue())

    @patch('myapp.management.commands.mycommand.open')
    def test_file_operations(self, mock_open):
        """Test command with mocked file operations"""
        mock_file = MagicMock()
        mock_file.read.return_value = 'test data'
        mock_open.return_value.__enter__.return_value = mock_file

        call_command('mycommand', 'test.txt')

        mock_open.assert_called_once_with('test.txt', 'r')
```

### Testing Async Commands

```python
from django.core.management import call_command
from django.test import TestCase
import asyncio

class TestAsyncCommand(TestCase):
    def test_async_command(self):
        """Test async command execution"""
        out = StringIO()
        call_command('async_command', stdout=out)

        output = out.getvalue()
        self.assertIn('Async operation complete', output)

    def test_async_operations(self):
        """Test async operations within command"""
        from myapp.models import MyModel

        call_command('async_command', '--count=10')

        # Verify async operations completed
        self.assertEqual(MyModel.objects.count(), 10)
```

### Testing with Test Databases

```python
from django.core.management import call_command
from django.test import TestCase

class TestMultipleDatabase(TestCase):
    databases = {'default', 'secondary'}

    def test_multi_database_operation(self):
        """Test command with multiple databases"""
        call_command('mycommand', '--database=secondary')

        from myapp.models import MyModel

        # Check record created in secondary database
        self.assertTrue(
            MyModel.objects.using('secondary').exists()
        )
```

### Performance Testing

```python
from django.core.management import call_command
from django.test import TestCase
import time

class TestPerformance(TestCase):
    def test_command_performance(self):
        """Test command completes within time limit"""
        from myapp.models import MyModel

        # Create test data
        MyModel.objects.bulk_create([
            MyModel(name=f'Item {i}') for i in range(1000)
        ])

        start_time = time.time()
        call_command('mycommand')
        elapsed = time.time() - start_time

        # Should complete within 5 seconds
        self.assertLess(elapsed, 5.0)

    def test_memory_efficiency(self):
        """Test command handles large datasets efficiently"""
        import tracemalloc
        from myapp.models import MyModel

        # Create large dataset
        MyModel.objects.bulk_create([
            MyModel(name=f'Item {i}') for i in range(100000)
        ])

        tracemalloc.start()
        call_command('mycommand')
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable (< 100MB)
        self.assertLess(peak / 1024 / 1024, 100)
```

### Integration Testing

```python
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch
import os

class TestIntegration(TestCase):
    def setUp(self):
        """Create temporary test files"""
        self.test_file = '/tmp/test_data.csv'
        with open(self.test_file, 'w') as f:
            f.write('name,value\n')
            f.write('test1,100\n')
            f.write('test2,200\n')

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_end_to_end_import(self):
        """Test complete import workflow"""
        from myapp.models import MyModel

        out = StringIO()
        call_command('import_data', self.test_file, stdout=out)

        # Verify import
        self.assertEqual(MyModel.objects.count(), 2)
        self.assertEqual(MyModel.objects.filter(name='test1').first().value, 100)

        # Verify output
        output = out.getvalue()
        self.assertIn('Imported 2 records', output)
```

### Testing Interactive Commands

```python
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

class TestInteractiveCommand(TestCase):
    @patch('builtins.input', return_value='yes')
    def test_confirmation_yes(self, mock_input):
        """Test command proceeds with 'yes' confirmation"""
        out = StringIO()
        call_command('mycommand', stdout=out)

        mock_input.assert_called_once()
        self.assertIn('Processing', out.getvalue())

    @patch('builtins.input', return_value='no')
    def test_confirmation_no(self, mock_input):
        """Test command cancels with 'no' confirmation"""
        out = StringIO()
        call_command('mycommand', stdout=out)

        mock_input.assert_called_once()
        self.assertIn('Cancelled', out.getvalue())

    def test_no_input_flag(self):
        """Test --no-input skips confirmation"""
        out = StringIO()
        call_command('mycommand', '--no-input', stdout=out)

        # Should proceed without asking
        self.assertIn('Processing', out.getvalue())
```

## Complete Test Suite Example

```python
from io import StringIO
from django.core.management import call_command, CommandError
from django.test import TestCase, TransactionTestCase
from unittest.mock import patch, MagicMock
from myapp.models import MyModel

class CommandTestCase(TestCase):
    """Base test case with common setup"""

    def setUp(self):
        """Create common test data"""
        self.item1 = MyModel.objects.create(name='Item 1', status='active')
        self.item2 = MyModel.objects.create(name='Item 2', status='pending')

    def call_command_with_output(self, *args, **kwargs):
        """Helper to call command and capture output"""
        out = StringIO()
        err = StringIO()
        call_command(*args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()


class TestMyCommandBasics(CommandTestCase):
    """Test basic command functionality"""

    def test_command_runs(self):
        """Test command executes successfully"""
        stdout, stderr = self.call_command_with_output('mycommand')
        self.assertIn('Success', stdout)
        self.assertEqual('', stderr)

    def test_command_with_args(self):
        """Test command with arguments"""
        stdout, _ = self.call_command_with_output('mycommand', '--limit=10')
        self.assertIn('Processed 2', stdout)


class TestMyCommandArguments(CommandTestCase):
    """Test argument handling"""

    def test_required_arguments(self):
        """Test required arguments are validated"""
        with self.assertRaises(SystemExit):
            call_command('mycommand')

    def test_optional_arguments(self):
        """Test optional arguments work correctly"""
        stdout, _ = self.call_command_with_output(
            'mycommand', 'required_arg', '--optional=value'
        )
        self.assertIn('optional: value', stdout)


class TestMyCommandDatabase(CommandTestCase):
    """Test database operations"""

    def test_creates_records(self):
        """Test record creation"""
        initial_count = MyModel.objects.count()
        call_command('mycommand', '--create')
        self.assertGreater(MyModel.objects.count(), initial_count)

    def test_updates_records(self):
        """Test record updates"""
        call_command('mycommand', '--update')
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.status, 'processed')

    def test_dry_run_mode(self):
        """Test dry-run doesn't modify database"""
        initial_count = MyModel.objects.count()
        call_command('mycommand', '--delete', '--dry-run')
        self.assertEqual(MyModel.objects.count(), initial_count)


class TestMyCommandErrors(CommandTestCase):
    """Test error handling"""

    def test_handles_validation_errors(self):
        """Test validation error handling"""
        with self.assertRaises(CommandError) as cm:
            call_command('mycommand', '--invalid-value')
        self.assertIn('Validation failed', str(cm.exception))

    def test_continues_on_error_with_flag(self):
        """Test --skip-errors flag"""
        stdout, stderr = self.call_command_with_output(
            'mycommand', '--trigger-errors', '--skip-errors'
        )
        self.assertIn('Completed with errors', stdout)
        self.assertIn('Error', stderr)


class TestMyCommandTransactions(TransactionTestCase):
    """Test transaction behavior"""

    def test_rollback_on_failure(self):
        """Test transaction rolls back on failure"""
        MyModel.objects.create(name='Test', status='active')
        initial_count = MyModel.objects.count()

        with self.assertRaises(CommandError):
            call_command('mycommand', '--fail-transaction')

        self.assertEqual(MyModel.objects.count(), initial_count)
```

## Best Practices

1. **Use StringIO for output capture** - Test both stdout and stderr
2. **Test all code paths** - Success, failure, and edge cases
3. **Test with different arguments** - Validate all combinations
4. **Use fixtures for complex data** - Consistent test data
5. **Mock external dependencies** - API calls, file operations
6. **Test transaction behavior** - Use TransactionTestCase when needed
7. **Test error messages** - Verify helpful error output
8. **Test performance** - Ensure commands scale appropriately
9. **Test idempotency** - Commands should be safe to re-run
10. **Create helper methods** - Reduce test code duplication
