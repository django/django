# Database Transactions and Patterns

This reference covers database operations, transactions, batch processing, and memory-efficient patterns in Django management commands.

## Table of Contents
- [Transaction Basics](#transaction-basics)
- [Dry-Run Mode](#dry-run-mode)
- [Batch Processing](#batch-processing)
- [Memory-Efficient Patterns](#memory-efficient-patterns)
- [Multi-Database Operations](#multi-database-operations)
- [Advanced Patterns](#advanced-patterns)

## Transaction Basics

### Default Behavior

By default, Django management commands run in **autocommit mode** - each database operation commits immediately:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Each operation commits immediately
        obj1 = MyModel.objects.create(name='first')   # Committed
        obj2 = MyModel.objects.create(name='second')  # Committed

        # If this fails, obj1 and obj2 are already in database
        obj3 = MyModel.objects.create(name='third')
```

### Atomic Transactions

Use `transaction.atomic()` to ensure all-or-nothing behavior:

```python
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.atomic():
            # All operations succeed or all fail
            obj1 = MyModel.objects.create(name='first')
            obj2 = MyModel.objects.create(name='second')
            obj3 = MyModel.objects.create(name='third')

            # If obj3 fails, obj1 and obj2 are rolled back
```

### Decorator Form

```python
from django.db import transaction

class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        # Entire handle() method runs in transaction
        MyModel.objects.create(name='first')
        MyModel.objects.create(name='second')
```

### Nested Transactions (Savepoints)

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.atomic():
            # Outer transaction
            obj1 = MyModel.objects.create(name='first')

            try:
                with transaction.atomic():
                    # Inner transaction (savepoint)
                    obj2 = MyModel.objects.create(name='second')
                    raise Exception('Oops!')
            except Exception:
                # obj2 is rolled back, but obj1 remains
                pass

            obj3 = MyModel.objects.create(name='third')
            # obj1 and obj3 are committed
```

### Manual Transaction Control

```python
from django.db import transaction, connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Start transaction manually
        transaction.set_autocommit(False)

        try:
            MyModel.objects.create(name='first')
            MyModel.objects.create(name='second')

            # Commit manually
            transaction.commit()
        except Exception as e:
            # Rollback on error
            transaction.rollback()
            self.stderr.write(f'Transaction failed: {e}')
        finally:
            # Restore autocommit
            transaction.set_autocommit(True)
```

### Rollback on Validation Errors

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        items_to_process = self.load_items()

        # Validate before committing
        with transaction.atomic():
            created = []

            for item_data in items_to_process:
                obj = MyModel(**item_data)
                # Validate without saving
                obj.full_clean()
                created.append(obj)

            # All valid - save in bulk
            MyModel.objects.bulk_create(created)

        # If any validation fails, nothing is saved
```

## Dry-Run Mode

Always implement dry-run mode for destructive operations.

### Basic Dry-Run Pattern

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Delete old records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them'
        )

    def handle(self, *args, **options):
        items = MyModel.objects.filter(status='obsolete')
        count = items.count()

        if options['dry_run']:
            # Show what would happen
            self.stdout.write(self.style.NOTICE(
                f'DRY RUN: Would delete {count} items'
            ))

            # Optionally show sample items
            if options['verbosity'] >= 2:
                for item in items[:5]:
                    self.stdout.write(f'  - {item}')

            return

        # Actually perform deletion
        items.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} items'))
```

### Dry-Run with Detailed Preview

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Gather changes
        updates = self.calculate_updates()
        creates = self.calculate_creates()
        deletes = self.calculate_deletes()

        # Show preview
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Changes Summary:')
        self.stdout.write(f'  Updates: {len(updates)}')
        self.stdout.write(f'  Creates: {len(creates)}')
        self.stdout.write(f'  Deletes: {len(deletes)}')
        self.stdout.write('=' * 50 + '\n')

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                'DRY RUN: No changes applied'
            ))
            return

        # Apply changes
        self.apply_changes(updates, creates, deletes)
        self.stdout.write(self.style.SUCCESS('Changes applied'))
```

### Dry-Run with Transaction Rollback

```python
from django.db import transaction

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Perform operations
                results = self.perform_operations()

                # Show results
                self.stdout.write(f'Processed {results["count"]} items')
                self.stdout.write(f'Changes: {results["changes"]}')

                # Rollback if dry-run
                if options['dry_run']:
                    self.stdout.write(self.style.NOTICE(
                        'DRY RUN: Rolling back all changes'
                    ))
                    # Raise exception to trigger rollback
                    raise transaction.TransactionManagementError(
                        'Dry run - rolling back'
                    )

        except transaction.TransactionManagementError:
            # Expected for dry-run
            pass
```

### Interactive Confirmation

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--no-input', action='store_true',
                          help='Skip confirmation prompt')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        items = MyModel.objects.filter(status='old')
        count = items.count()

        # Show what will happen
        self.stdout.write(f'About to delete {count} items')

        if options['verbosity'] >= 2:
            for item in items[:10]:
                self.stdout.write(f'  - {item}')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')

        # Skip confirmation if --no-input or --dry-run
        if not options['no_input'] and not options['dry_run']:
            confirm = input('\nAre you sure? Type "yes" to continue: ')
            if confirm != 'yes':
                self.stdout.write('Cancelled')
                return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE('DRY RUN: No changes made'))
            return

        # Perform deletion
        deleted, _ = items.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} items'))
```

## Batch Processing

### Bulk Create

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        data = self.load_data()

        batch = []
        created = 0

        for item_data in data:
            batch.append(MyModel(**item_data))

            if len(batch) >= batch_size:
                MyModel.objects.bulk_create(batch)
                created += len(batch)
                batch = []

                if options['verbosity'] >= 1:
                    self.stdout.write(f'Created {created} items...')

        # Create remaining items
        if batch:
            MyModel.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Created {created} items'))
```

### Bulk Update

```python
from django.db.models import F

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Update all at once (single query)
        updated = MyModel.objects.filter(status='pending').update(
            status='processed',
            processed_at=timezone.now()
        )
        self.stdout.write(f'Updated {updated} items')

        # Or use F expressions for complex updates
        MyModel.objects.filter(status='active').update(
            view_count=F('view_count') + 1
        )
```

### Bulk Update with Individual Changes

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        items = MyModel.objects.filter(needs_update=True)

        batch = []
        for item in items.iterator(chunk_size=batch_size):
            # Make individual changes
            item.calculated_field = self.calculate_value(item)
            batch.append(item)

            if len(batch) >= batch_size:
                # Bulk update
                MyModel.objects.bulk_update(
                    batch,
                    ['calculated_field'],
                    batch_size=batch_size
                )
                self.stdout.write(f'Updated {len(batch)} items')
                batch = []

        # Update remaining items
        if batch:
            MyModel.objects.bulk_update(batch, ['calculated_field'])
```

### Batch Delete

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        batch_size = options['batch_size']

        total_deleted = 0
        while True:
            # Delete in batches to avoid locking large tables
            ids = list(
                MyModel.objects
                .filter(status='obsolete')
                .values_list('id', flat=True)[:batch_size]
            )

            if not ids:
                break

            deleted, _ = MyModel.objects.filter(id__in=ids).delete()
            total_deleted += deleted

            self.stdout.write(f'Deleted {total_deleted} items...')

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {total_deleted} items total'
        ))
```

### Transaction Per Batch

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        batch_size = 1000
        data = self.load_data()

        total_created = 0
        batch = []

        for item_data in data:
            batch.append(MyModel(**item_data))

            if len(batch) >= batch_size:
                # Each batch in its own transaction
                with transaction.atomic():
                    MyModel.objects.bulk_create(batch)
                    total_created += len(batch)

                self.stdout.write(f'Created {total_created} items...')
                batch = []

        # Final batch
        if batch:
            with transaction.atomic():
                MyModel.objects.bulk_create(batch)
                total_created += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f'Created {total_created} items'
        ))
```

## Memory-Efficient Patterns

### Using iterator()

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Bad - loads all objects into memory
        # for item in MyModel.objects.all():
        #     self.process_item(item)

        # Good - streams results from database
        for item in MyModel.objects.all().iterator(chunk_size=2000):
            self.process_item(item)
```

### Limiting Selected Fields

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Only load needed fields
        for item in MyModel.objects.only('id', 'name').iterator():
            self.stdout.write(f'{item.id}: {item.name}')

        # Or defer large fields
        for item in MyModel.objects.defer('large_text_field').iterator():
            self.process_item(item)
```

### values() and values_list()

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Return dictionaries instead of model instances
        for item_dict in MyModel.objects.values('id', 'name').iterator():
            self.stdout.write(f'{item_dict["id"]}: {item_dict["name"]}')

        # Return tuples for even less memory
        for item_id, name in MyModel.objects.values_list('id', 'name').iterator():
            self.stdout.write(f'{item_id}: {name}')

        # Single value
        for item_id in MyModel.objects.values_list('id', flat=True).iterator():
            self.process_id(item_id)
```

### Chunked Processing with Explicit Memory Management

```python
import gc

class Command(BaseCommand):
    def handle(self, *args, **options):
        chunk_size = 10000
        offset = 0

        while True:
            # Process in chunks
            items = list(
                MyModel.objects.all()[offset:offset + chunk_size]
            )

            if not items:
                break

            for item in items:
                self.process_item(item)

            offset += chunk_size

            # Clear Django query cache and force garbage collection
            from django.db import reset_queries
            reset_queries()
            gc.collect()

            self.stdout.write(f'Processed {offset} items...')
```

### Raw SQL for Large Operations

```python
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Process with raw SQL for better memory efficiency
            cursor.execute('''
                SELECT id, name, status
                FROM myapp_mymodel
                WHERE status = %s
            ''', ['pending'])

            while True:
                rows = cursor.fetchmany(size=1000)
                if not rows:
                    break

                for row in rows:
                    item_id, name, status = row
                    self.process_item(item_id, name, status)
```

### Server-Side Cursors (PostgreSQL)

```python
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Use server-side cursor for large result sets
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM myapp_mymodel',
                cursor_kwargs={'name': 'large_result_set'}
            )

            while True:
                rows = cursor.fetchmany(size=1000)
                if not rows:
                    break

                for row in rows:
                    self.process_row(row)
```

## Multi-Database Operations

### Specifying Database

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default='default',
            help='Database alias to use'
        )

    def handle(self, *args, **options):
        database = options['database']

        # Validate database exists
        if database not in connections:
            raise CommandError(f'Database "{database}" not configured')

        # Use specific database
        items = MyModel.objects.using(database).all()

        # Create in specific database
        MyModel.objects.using(database).create(name='test')

        self.stdout.write(f'Processed {items.count()} items from {database}')
```

### Cross-Database Operations

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Use separate transactions for each database
        with transaction.atomic(using='default'):
            obj1 = MyModel.objects.using('default').create(name='test')

        with transaction.atomic(using='replica'):
            obj2 = OtherModel.objects.using('replica').create(ref=obj1.id)
```

### Replication Lag Handling

```python
import time
from django.db import connections

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Write to primary
        obj = MyModel.objects.using('default').create(name='test')

        # Wait for replication
        self.wait_for_replication('replica', timeout=10)

        # Read from replica
        replicated = MyModel.objects.using('replica').filter(id=obj.id).first()

        if replicated:
            self.stdout.write('Replication confirmed')
        else:
            self.stderr.write('Replication lag detected')

    def wait_for_replication(self, database, timeout):
        """Wait for replica to catch up"""
        time.sleep(0.1)  # Simple wait; implement proper check for production
```

## Advanced Patterns

### Progress Tracking Table

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Track progress in database table
        progress, created = CommandProgress.objects.get_or_create(
            command_name='my_command',
            defaults={'last_processed_id': 0}
        )

        # Resume from last position
        items = MyModel.objects.filter(
            id__gt=progress.last_processed_id
        ).order_by('id')

        for item in items.iterator():
            with transaction.atomic():
                self.process_item(item)

                # Update progress
                progress.last_processed_id = item.id
                progress.last_run = timezone.now()
                progress.save()
```

### Concurrent Processing with Database Locks

```python
from django.db import transaction
from django.db.models import F

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Select and lock items for processing
        with transaction.atomic():
            items = list(
                MyModel.objects
                .select_for_update(skip_locked=True)
                .filter(status='pending')[:100]
            )

            for item in items:
                # Mark as processing
                item.status = 'processing'
                item.save()

        # Process outside transaction
        for item in items:
            try:
                self.process_item(item)
                item.status = 'completed'
            except Exception as e:
                item.status = 'failed'
                item.error = str(e)
            finally:
                item.save()
```

### Two-Phase Commit Pattern

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Phase 1: Prepare changes
        changes = []
        with transaction.atomic():
            items = MyModel.objects.select_for_update().filter(status='pending')

            for item in items:
                # Validate and prepare
                if self.validate_item(item):
                    changes.append(item)
                    item.status = 'prepared'
                    item.save()

        # Phase 2: Commit changes
        with transaction.atomic():
            for item in changes:
                try:
                    self.apply_changes(item)
                    item.status = 'completed'
                    item.save()
                except Exception as e:
                    item.status = 'failed'
                    item.error = str(e)
                    item.save()
```

### Idempotent Operations

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Safe to run multiple times
        data = self.load_data()

        for item_data in data:
            # Use get_or_create for idempotency
            obj, created = MyModel.objects.get_or_create(
                external_id=item_data['external_id'],
                defaults=item_data
            )

            if not created:
                # Update existing record
                for key, value in item_data.items():
                    setattr(obj, key, value)
                obj.save()

            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} {obj}')
```

### Deadlock Handling

```python
from django.db import transaction
from django.db.utils import OperationalError
import time

class Command(BaseCommand):
    def handle(self, *args, **options):
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Operations that might deadlock
                    self.perform_operations()
                    break  # Success
            except OperationalError as e:
                if 'deadlock' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt  # Exponential backoff
                        self.stdout.write(f'Deadlock detected, retrying in {wait}s...')
                        time.sleep(wait)
                    else:
                        raise
                else:
                    raise
```

## Best Practices

1. **Use transactions for data integrity** - Wrap related operations in `transaction.atomic()`
2. **Implement dry-run mode** - Always provide preview for destructive operations
3. **Batch operations** - Use bulk_create/bulk_update for better performance
4. **Stream large querysets** - Use `.iterator()` to avoid memory issues
5. **Handle rollbacks gracefully** - Use try/except with transaction blocks
6. **Track progress** - Store checkpoint data for resumable operations
7. **Test transaction behavior** - Verify rollback and commit scenarios
8. **Consider database locks** - Use `select_for_update()` for concurrent operations
9. **Monitor memory usage** - Use `only()`, `defer()`, or `values()` for large datasets
10. **Make operations idempotent** - Safe to run multiple times with same result
