# Command Output Patterns

This reference covers output handling, styling, progress reporting, and error handling in Django management commands.

## Table of Contents
- [Basic Output](#basic-output)
- [Styled Output](#styled-output)
- [Verbosity Levels](#verbosity-levels)
- [Progress Reporting](#progress-reporting)
- [Error Handling](#error-handling)
- [Logging Integration](#logging-integration)

## Basic Output

### stdout vs stderr

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Normal output to stdout
        self.stdout.write('Processing started')

        # Error/warning output to stderr
        self.stderr.write('Warning: Low disk space')

        # Python's print() also works but less recommended
        print('This goes to stdout')
```

**Why use `self.stdout` and `self.stderr`?**
- Allows output redirection in tests
- Respects Django's color settings
- Consistent with Django conventions
- Easier to capture and test

### Writing Without Newlines

```python
# Write without newline (for progress updates)
self.stdout.write('Processing... ', ending='')
self.stdout.write('Done')

# Output: Processing... Done
```

### Flushing Output

```python
import sys

# Force output immediately (useful for long-running commands)
self.stdout.write('Starting...')
self.stdout.flush()  # Ensure it's displayed immediately

# For real-time progress updates
for i in range(100):
    self.stdout.write(f'\rProgress: {i}%', ending='')
    sys.stdout.flush()
```

## Styled Output

Django provides built-in style methods for consistent, colored output.

### Available Styles

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Success (green)
        self.stdout.write(self.style.SUCCESS('Operation completed successfully'))

        # Error (red)
        self.stdout.write(self.style.ERROR('Operation failed'))

        # Warning (yellow)
        self.stdout.write(self.style.WARNING('Deprecated feature used'))

        # Notice (bright/bold)
        self.stdout.write(self.style.NOTICE('Important information'))

        # SQL styles
        self.stdout.write(self.style.SQL_FIELD('field_name'))
        self.stdout.write(self.style.SQL_COLTYPE('VARCHAR(255)'))
        self.stdout.write(self.style.SQL_KEYWORD('SELECT'))
        self.stdout.write(self.style.SQL_TABLE('my_table'))

        # HTTP styles
        self.stdout.write(self.style.HTTP_INFO('200 OK'))
        self.stdout.write(self.style.HTTP_SUCCESS('201 Created'))
        self.stdout.write(self.style.HTTP_REDIRECT('302 Found'))
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('304 Not Modified'))
        self.stdout.write(self.style.HTTP_BAD_REQUEST('400 Bad Request'))
        self.stdout.write(self.style.HTTP_NOT_FOUND('404 Not Found'))
        self.stdout.write(self.style.HTTP_SERVER_ERROR('500 Internal Server Error'))

        # Migration styles
        self.stdout.write(self.style.MIGRATE_HEADING('Running migrations:'))
        self.stdout.write(self.style.MIGRATE_LABEL('  Applying myapp.0001_initial'))
```

### Style Reference Table

| Style | Color | Use Case |
|-------|-------|----------|
| `SUCCESS` | Green | Successful operations |
| `ERROR` | Red | Errors, failures |
| `WARNING` | Yellow | Warnings, deprecations |
| `NOTICE` | Bright/Bold | Important notices |
| `SQL_FIELD` | Purple | Database field names |
| `SQL_COLTYPE` | Orange | Column types |
| `SQL_KEYWORD` | Cyan | SQL keywords |
| `SQL_TABLE` | Yellow | Table names |
| `HTTP_INFO` | Blue | HTTP 1xx-2xx status |
| `HTTP_SUCCESS` | Green | HTTP 2xx status |
| `HTTP_REDIRECT` | Cyan | HTTP 3xx status |
| `HTTP_NOT_MODIFIED` | Cyan | HTTP 304 |
| `HTTP_BAD_REQUEST` | Red | HTTP 4xx status |
| `HTTP_NOT_FOUND` | Red | HTTP 404 |
| `HTTP_SERVER_ERROR` | Red | HTTP 5xx status |
| `MIGRATE_HEADING` | Cyan | Migration section headers |
| `MIGRATE_LABEL` | None | Individual migrations |

### Disabling Colors

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        # --no-color is automatically added by Django
        pass

    def handle(self, *args, **options):
        # Colors are automatically disabled when:
        # 1. --no-color flag is used
        # 2. stdout is not a TTY (e.g., piped to file)
        # 3. DJANGO_COLORS environment variable is set

        self.stdout.write(self.style.SUCCESS('This may or may not be colored'))
```

### Custom Styling

```python
from django.core.management.color import no_style, color_style

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Use custom color scheme
        if options.get('no_color'):
            self.style = no_style()
        else:
            self.style = color_style()

        # Or use termcolor directly
        from django.utils.termcolors import make_style

        custom_style = make_style(fg='blue', opts=('bold',))
        self.stdout.write(custom_style('Custom styled text'))
```

## Verbosity Levels

Django commands automatically support `--verbosity` (0-3).

### Standard Verbosity Levels

| Level | Flag | Use Case | Example |
|-------|------|----------|---------|
| 0 | `--verbosity 0` | Silent (errors only) | Cron jobs |
| 1 | Default | Normal output | Standard use |
| 2 | `--verbosity 2` | Verbose | Debugging |
| 3 | `--verbosity 3` | Very verbose | Deep debugging |

### Using Verbosity Levels

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        verbosity = options['verbosity']

        # Always show (even at verbosity 0)
        if verbosity >= 0:
            self.stdout.write(self.style.ERROR('Critical error occurred'))

        # Normal output (verbosity 1+)
        if verbosity >= 1:
            self.stdout.write('Processing 100 items...')

        # Verbose output (verbosity 2+)
        if verbosity >= 2:
            self.stdout.write('  Processing item #1: widget_a')
            self.stdout.write('  Processing item #2: widget_b')

        # Debug output (verbosity 3)
        if verbosity >= 3:
            self.stdout.write('  Database query: SELECT * FROM widgets')
            self.stdout.write('  Query took: 0.05ms')
```

### Best Practices for Verbosity

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        verbosity = options['verbosity']

        # Level 0: Critical errors only
        # (These should always be shown)

        # Level 1: High-level progress
        if verbosity >= 1:
            self.stdout.write('Starting import...')
            self.stdout.write(f'Processed {count} records')
            self.stdout.write(self.style.SUCCESS('Import complete'))

        # Level 2: Detailed progress
        if verbosity >= 2:
            for i, record in enumerate(records):
                self.stdout.write(f'  Record {i+1}/{total}: {record.name}')

        # Level 3: Debug information
        if verbosity >= 3:
            self.stdout.write(f'  Memory usage: {memory_usage()}')
            self.stdout.write(f'  Query count: {len(connection.queries)}')
```

## Progress Reporting

### Simple Counter

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        items = MyModel.objects.all()
        total = items.count()
        processed = 0

        for item in items:
            self.process_item(item)
            processed += 1

            if options['verbosity'] >= 1 and processed % 100 == 0:
                self.stdout.write(f'Processed {processed}/{total}')

        self.stdout.write(self.style.SUCCESS(
            f'Successfully processed {processed} items'
        ))
```

### Percentage Progress

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        items = MyModel.objects.all()
        total = items.count()

        for i, item in enumerate(items, 1):
            self.process_item(item)

            # Update every 10%
            if i % (total // 10) == 0 or i == total:
                percentage = (i * 100) // total
                self.stdout.write(f'Progress: {percentage}%')
```

### Progress Bar with tqdm

```python
from django.core.management.base import BaseCommand
from tqdm import tqdm

class Command(BaseCommand):
    def handle(self, *args, **options):
        items = MyModel.objects.all()
        total = items.count()

        # Disable tqdm if not verbose
        disable_progress = options['verbosity'] < 1

        for item in tqdm(
            items.iterator(),
            total=total,
            desc='Processing',
            disable=disable_progress
        ):
            self.process_item(item)

        self.stdout.write(self.style.SUCCESS('Complete'))
```

### Manual Progress Bar

```python
import sys

class Command(BaseCommand):
    def handle(self, *args, **options):
        items = list(MyModel.objects.all())
        total = len(items)

        for i, item in enumerate(items, 1):
            self.process_item(item)

            # Update progress bar
            self.update_progress(i, total)

        # Clear progress bar and show completion
        self.stdout.write('\n' + self.style.SUCCESS('Complete'))

    def update_progress(self, current, total):
        """Display progress bar"""
        bar_length = 50
        filled = int(bar_length * current / total)
        bar = '█' * filled + '-' * (bar_length - filled)
        percent = 100 * current / total

        self.stdout.write(
            f'\r[{bar}] {percent:.1f}% ({current}/{total})',
            ending=''
        )
        self.stdout.flush()
```

### Multi-Stage Progress

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Stage 1: Loading data'))
        data = self.load_data()
        self.stdout.write(self.style.SUCCESS(f'  Loaded {len(data)} records'))

        self.stdout.write(self.style.MIGRATE_HEADING('Stage 2: Validating'))
        valid, invalid = self.validate_data(data)
        self.stdout.write(self.style.SUCCESS(f'  Valid: {len(valid)}'))
        if invalid:
            self.stdout.write(self.style.WARNING(f'  Invalid: {len(invalid)}'))

        self.stdout.write(self.style.MIGRATE_HEADING('Stage 3: Processing'))
        results = self.process_data(valid)
        self.stdout.write(self.style.SUCCESS(f'  Processed: {len(results)}'))

        self.stdout.write(self.style.SUCCESS('\nAll stages complete'))
```

### Real-Time Statistics

```python
import time

class Command(BaseCommand):
    def handle(self, *args, **options):
        items = MyModel.objects.all()
        total = items.count()

        start_time = time.time()
        processed = 0
        errors = 0

        for item in items:
            try:
                self.process_item(item)
                processed += 1
            except Exception:
                errors += 1

            # Show stats every 100 items
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = (total - processed) / rate if rate > 0 else 0

                self.stdout.write(
                    f'Processed: {processed}/{total} '
                    f'({rate:.1f}/sec, ~{remaining:.0f}s remaining)'
                )

        # Final summary
        total_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f'\nCompleted in {total_time:.2f}s\n'
            f'Processed: {processed}\n'
            f'Errors: {errors}'
        ))
```

## Error Handling

### CommandError

Use `CommandError` for user-facing errors (incorrect usage, validation failures):

```python
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    def handle(self, *args, **options):
        user_id = options['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'User {user_id} does not exist')

        # CommandError exits with code 1 and displays the error message
```

### Exception Handling

```python
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        items = MyModel.objects.all()
        errors = []

        for item in items:
            try:
                self.process_item(item)
            except ValidationError as e:
                # Expected error - collect and report
                errors.append((item, str(e)))
                self.stderr.write(
                    self.style.WARNING(f'Validation failed for {item}: {e}')
                )
            except Exception as e:
                # Unexpected error - log and possibly abort
                logger.exception(f'Unexpected error processing {item}')
                self.stderr.write(
                    self.style.ERROR(f'Error processing {item}: {e}')
                )
                if not options.get('skip_errors'):
                    raise

        # Report errors summary
        if errors:
            self.stdout.write(self.style.WARNING(
                f'\n{len(errors)} items failed validation'
            ))
            if not options.get('continue_on_errors'):
                raise CommandError('Processing incomplete due to errors')
```

### Graceful Degradation

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Try optimal approach
        try:
            self.process_with_bulk_operations()
        except Exception as e:
            self.stderr.write(self.style.WARNING(
                f'Bulk operation failed: {e}. Falling back to individual processing.'
            ))
            # Fall back to slower but more reliable approach
            self.process_individually()
```

### Error Summary

```python
from collections import defaultdict

class Command(BaseCommand):
    def handle(self, *args, **options):
        error_counts = defaultdict(int)
        success_count = 0

        for item in items:
            try:
                self.process_item(item)
                success_count += 1
            except ValidationError as e:
                error_counts['validation'] += 1
            except IntegrityError as e:
                error_counts['integrity'] += 1
            except Exception as e:
                error_counts['other'] += 1
                logger.exception(f'Unexpected error: {e}')

        # Display summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'Successful: {success_count}'))

        if error_counts:
            self.stdout.write(self.style.WARNING('\nErrors:'))
            for error_type, count in error_counts.items():
                self.stdout.write(f'  {error_type}: {count}')

        if sum(error_counts.values()) > 0:
            raise CommandError('Processing completed with errors')
```

## Logging Integration

### Basic Logging Setup

```python
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Configure logging level based on verbosity
        if options['verbosity'] >= 2:
            logger.setLevel(logging.DEBUG)
        elif options['verbosity'] >= 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        logger.info('Command started')

        # Command logic...

        logger.info('Command completed')
```

### File Logging

```python
import logging
from django.conf import settings

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--log-file',
            type=str,
            help='Write log to file'
        )

    def handle(self, *args, **options):
        # Setup file logging if requested
        if options['log_file']:
            handler = logging.FileHandler(options['log_file'])
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            logger = logging.getLogger(__name__)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        # Use both logger and stdout
        logger.info('Processing started')
        self.stdout.write('Processing started')

        # Process items...

        logger.info(f'Processed {count} items')
        self.stdout.write(self.style.SUCCESS(f'Processed {count} items'))
```

### Structured Logging

```python
import logging
import json

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--json-output',
            action='store_true',
            help='Output in JSON format'
        )

    def handle(self, *args, **options):
        json_output = options['json_output']

        def log_message(level, message, **kwargs):
            if json_output:
                data = {'level': level, 'message': message, **kwargs}
                self.stdout.write(json.dumps(data))
            else:
                style = getattr(self.style, level.upper(), None)
                if style:
                    self.stdout.write(style(message))
                else:
                    self.stdout.write(message)

        log_message('info', 'Processing started')
        log_message('success', 'Processed items', count=100)
        log_message('error', 'Failed to process', item_id=42)
```

## Complete Real-World Example

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import and process data with comprehensive output handling'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Input file')
        parser.add_argument('--batch-size', type=int, default=1000)
        parser.add_argument('--skip-errors', action='store_true')

    def handle(self, *args, **options):
        file_path = options['file']
        batch_size = options['batch_size']
        skip_errors = options['skip_errors']
        verbosity = options['verbosity']

        # Header
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\nData Import Command\n{"=" * 60}'
        ))

        # Load data
        self.stdout.write(self.style.MIGRATE_HEADING('\nStage 1: Loading data'))
        try:
            data = self.load_data(file_path)
            self.stdout.write(self.style.SUCCESS(
                f'  Loaded {len(data)} records'
            ))
        except Exception as e:
            raise CommandError(f'Failed to load data: {e}')

        # Validate
        self.stdout.write(self.style.MIGRATE_HEADING('\nStage 2: Validation'))
        valid, invalid = self.validate_data(data, verbosity)
        self.stdout.write(self.style.SUCCESS(f'  Valid: {len(valid)}'))
        if invalid:
            self.stdout.write(self.style.WARNING(f'  Invalid: {len(invalid)}'))
            if not skip_errors:
                raise CommandError('Validation failed. Use --skip-errors to continue.')

        # Process
        self.stdout.write(self.style.MIGRATE_HEADING('\nStage 3: Processing'))
        start_time = time.time()

        try:
            stats = self.process_data(valid, batch_size, verbosity)
        except Exception as e:
            logger.exception('Processing failed')
            raise CommandError(f'Processing failed: {e}')

        elapsed = time.time() - start_time

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\nSummary\n{"=" * 60}'
        ))
        self.stdout.write(f'Total records: {len(data)}')
        self.stdout.write(self.style.SUCCESS(f'Processed: {stats["success"]}'))
        if stats['errors'] > 0:
            self.stdout.write(self.style.WARNING(f'Errors: {stats["errors"]}'))
        self.stdout.write(f'Time: {elapsed:.2f}s')
        self.stdout.write(f'Rate: {stats["success"]/elapsed:.1f} records/sec')

        self.stdout.write('\n' + self.style.SUCCESS('Import complete!') + '\n')

    def load_data(self, file_path):
        """Load data from file"""
        # Implementation
        return []

    def validate_data(self, data, verbosity):
        """Validate loaded data"""
        valid = []
        invalid = []

        for i, record in enumerate(data):
            is_valid, errors = self.validate_record(record)

            if is_valid:
                valid.append(record)
            else:
                invalid.append((record, errors))
                if verbosity >= 2:
                    self.stderr.write(f'  Record {i}: {errors}')

        return valid, invalid

    def validate_record(self, record):
        """Validate single record"""
        # Implementation
        return True, []

    def process_data(self, data, batch_size, verbosity):
        """Process valid data"""
        total = len(data)
        processed = 0
        errors = 0

        for i, record in enumerate(data, 1):
            try:
                self.process_record(record)
                processed += 1
            except Exception as e:
                errors += 1
                if verbosity >= 2:
                    self.stderr.write(self.style.ERROR(
                        f'  Error processing record {i}: {e}'
                    ))

            # Progress updates
            if verbosity >= 1 and i % 100 == 0:
                percentage = (i * 100) // total
                self.stdout.write(f'  Progress: {percentage}% ({i}/{total})')

        return {'success': processed, 'errors': errors}

    def process_record(self, record):
        """Process single record"""
        # Implementation
        pass
```

## Best Practices

1. **Use appropriate output streams** - `stdout` for normal output, `stderr` for errors
2. **Respect verbosity levels** - Show appropriate detail based on `--verbosity`
3. **Style consistently** - Use Django's built-in styles
4. **Provide progress updates** - For long-running commands
5. **Handle errors gracefully** - Catch, log, and report errors appropriately
6. **Write clear error messages** - Help users understand and fix issues
7. **Summarize results** - Show final statistics and outcomes
8. **Support machine-readable output** - Consider JSON format for automation
9. **Log important events** - Use logging module for persistent records
10. **Test output** - Capture and verify output in tests
