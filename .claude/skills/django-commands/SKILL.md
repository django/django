# Django Management Commands Skill

## Overview

This skill helps you create, enhance, and test Django management commands - the custom scripts you run with `python manage.py <command>`. Use this skill when you need to:

- Create data import/export commands
- Build maintenance and cleanup tasks
- Implement scheduled jobs and batch processing
- Add developer utilities and debugging tools
- Create deployment and migration helpers

Management commands are powerful tools for automation, data processing, and system maintenance that operate within Django's application context with full ORM access.

## When to Use This Skill

**Use Django management commands when you need:**
- Database operations requiring Django ORM
- Access to Django settings and configuration
- Commands run via cron, systemd, or CI/CD pipelines
- Batch processing with progress reporting
- Interactive data maintenance tools

**Don't use management commands when:**
- A simple Python script would suffice
- You need real-time request handling (use views instead)
- Celery/background tasks are more appropriate
- The operation should be triggered by user actions (use signals)

## Quick Start

Create a basic command in 3 steps:

1. **Create the command file:**
   ```bash
   mkdir -p myapp/management/commands
   touch myapp/management/commands/__init__.py
   touch myapp/management/commands/mycommand.py
   ```

2. **Write the command:**
   ```python
   from django.core.management.base import BaseCommand

   class Command(BaseCommand):
       help = 'Description of what this command does'

       def handle(self, *args, **options):
           self.stdout.write(self.style.SUCCESS('Command executed successfully'))
   ```

3. **Run it:**
   ```bash
   python manage.py mycommand
   ```

## Core Workflows

### Workflow 1: Create Basic Management Command

**When:** You need a simple command with no arguments.

**Steps:**
1. Create directory structure: `myapp/management/commands/`
2. Add `__init__.py` files to make packages
3. Create command file with `Command` class
4. Implement `handle()` method
5. Test with `python manage.py <command>`

**See:** [reference/base_classes.md](reference/base_classes.md) for base class options

### Workflow 2: Add Arguments and Options

**When:** Your command needs input parameters or flags.

**Steps:**
1. Override `add_arguments()` method
2. Add positional arguments with `parser.add_argument()`
3. Add optional flags with `parser.add_argument('--flag')`
4. Access in `handle()` via `options` dictionary
5. Validate inputs and provide helpful error messages

**See:** [reference/arguments.md](reference/arguments.md) for argument patterns

### Workflow 3: Implement Progress Reporting

**When:** Running long operations that process multiple items.

**Steps:**
1. Count total items before processing
2. Initialize progress tracking
3. Use `self.stdout.write()` for updates
4. Respect `--verbosity` option
5. Report completion statistics

**Example:**
```python
def handle(self, *args, **options):
    items = MyModel.objects.all()
    total = items.count()
    processed = 0

    for item in items:
        # Process item
        processed += 1
        if options['verbosity'] >= 1:
            self.stdout.write(f'Processed {processed}/{total}')

    self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed} items'))
```

**See:** [reference/output.md](reference/output.md) for output patterns

### Workflow 4: Handle Errors Gracefully

**When:** Your command can fail and you need proper error handling.

**Steps:**
1. Use try/except blocks for specific errors
2. Write errors to `self.stderr`
3. Raise `CommandError` for user-facing errors
4. Log unexpected errors
5. Exit with appropriate status codes

**Example:**
```python
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            obj = MyModel.objects.get(id=options['id'])
        except MyModel.DoesNotExist:
            raise CommandError(f'MyModel with id {options["id"]} does not exist')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Unexpected error: {e}'))
            raise
```

**See:** [reference/output.md](reference/output.md) for error handling

### Workflow 5: Test Management Commands

**When:** You need to verify command behavior and outputs.

**Steps:**
1. Import `call_command` from `django.core.management`
2. Use `StringIO` to capture output
3. Call command with arguments
4. Assert on output and side effects
5. Test error cases

**Example:**
```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class TestMyCommand(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command('mycommand', stdout=out)
        self.assertIn('Successfully', out.getvalue())
```

**See:** [reference/testing.md](reference/testing.md) for testing patterns

## Command Base Classes

Django provides three base classes for different use cases:

### BaseCommand
**Use for:** General-purpose commands with custom logic
- Most flexible, no assumptions about behavior
- Override `handle(*args, **options)` method
- Full control over argument parsing and execution

### AppCommand
**Use for:** Commands that operate on one or more apps
- Automatically handles app label arguments
- Override `handle_app_config(app_config, **options)`
- Validates app labels exist

### LabelCommand
**Use for:** Commands that operate on arbitrary labels/identifiers
- Processes one or more string arguments
- Override `handle_label(label, **options)`
- Good for file paths, IDs, or names

**See:** [reference/base_classes.md](reference/base_classes.md) for details and examples

## Database Operations

### Transactions
By default, commands run in autocommit mode. For atomic operations:

```python
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.atomic():
            # All operations succeed or all fail
            MyModel.objects.create(name='test')
```

### Dry-Run Mode
Always implement `--dry-run` for destructive operations:

```python
def add_arguments(self, parser):
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying them')

def handle(self, *args, **options):
    items_to_delete = MyModel.objects.filter(status='obsolete')
    count = items_to_delete.count()

    if options['dry_run']:
        self.stdout.write(f'Would delete {count} items (dry run)')
        return

    items_to_delete.delete()
    self.stdout.write(self.style.SUCCESS(f'Deleted {count} items'))
```

### Memory-Efficient Iteration
Use `iterator()` for large querysets:

```python
# Bad - loads all objects into memory
for item in MyModel.objects.all():
    process(item)

# Good - streams results
for item in MyModel.objects.all().iterator(chunk_size=2000):
    process(item)
```

**See:** [reference/transactions.md](reference/transactions.md) for database patterns

## Interactive Commands

For commands requiring user confirmation:

```python
def handle(self, *args, **options):
    items_to_delete = MyModel.objects.filter(status='old')
    count = items_to_delete.count()

    self.stdout.write(f'About to delete {count} items')

    if options.get('interactive', True):
        confirm = input('Are you sure? [y/N] ')
        if confirm.lower() != 'y':
            self.stdout.write('Cancelled')
            return

    items_to_delete.delete()
    self.stdout.write(self.style.SUCCESS('Deleted'))
```

Add `--no-input` flag for non-interactive mode (CI/CD):

```python
def add_arguments(self, parser):
    parser.add_argument('--no-input', action='store_true',
                       help='Do not prompt for input')

def handle(self, *args, **options):
    if not options['no_input']:
        # Prompt user
        pass
```

## Output Styling

Use built-in styles for consistent output:

```python
self.stdout.write(self.style.SUCCESS('Operation completed'))
self.stdout.write(self.style.ERROR('Operation failed'))
self.stdout.write(self.style.WARNING('Deprecation warning'))
self.stdout.write(self.style.NOTICE('FYI'))
self.stdout.write(self.style.SQL_FIELD('Field name'))
self.stdout.write(self.style.SQL_COLTYPE('VARCHAR'))
self.stdout.write(self.style.SQL_KEYWORD('SELECT'))
self.stdout.write(self.style.SQL_TABLE('table_name'))
self.stdout.write(self.style.HTTP_INFO('200 OK'))
self.stdout.write(self.style.HTTP_SUCCESS('Created'))
self.stdout.write(self.style.MIGRATE_HEADING('Running migrations'))
self.stdout.write(self.style.MIGRATE_LABEL('  Applying myapp.0001'))
```

**See:** [reference/output.md](reference/output.md) for output patterns

## Scripts & Tools

### Command Generator
Generate boilerplate for different command types:

```bash
python /home/user/django/.claude/skills/django-commands/scripts/generate_command.py \
    myapp \
    mycommand \
    --type base \
    --description "My command description"
```

**Types:**
- `base` - Basic command with arguments
- `import` - CSV/data import template
- `maintenance` - Cleanup/deletion with dry-run
- `report` - Analytics/reporting template
- `integration` - API sync template

**See:** [scripts/generate_command.py](scripts/generate_command.py)

## Common Patterns

**Bulk Data Import:**
```python
# Use bulk_create with batching
batch = []
for row in csv.DictReader(file):
    batch.append(MyModel(**row))
    if len(batch) >= 1000:
        MyModel.objects.bulk_create(batch)
        batch = []
```

**Scheduled Cleanup:**
```python
# Delete old records with dry-run support
cutoff = timezone.now() - timedelta(days=30)
items = MyModel.objects.filter(created_at__lt=cutoff)
if not options['dry_run']:
    items.delete()
```

**Data Export:**
```python
# Stream large exports with iterator()
for item in MyModel.objects.iterator():
    writer.writerow([item.id, item.name])
```

## Anti-Patterns

**❌ Ignore Error Handling** - Catch exceptions and report failures explicitly
**❌ Hardcode Values** - Use arguments and settings instead of magic numbers/paths
**❌ Load Everything Into Memory** - Use `.iterator()` for large querysets
**❌ Skip Dry-Run** - Always implement `--dry-run` for destructive operations
**❌ Ignore Transactions** - Wrap related operations in `transaction.atomic()`

**✅ Best Practices:**
```python
# Error handling with reporting
try:
    item.process()
except Exception as e:
    self.stderr.write(f'Failed: {e}')

# Memory-efficient iteration
for item in MyModel.objects.iterator(chunk_size=2000):
    process(item)

# Atomic transactions
with transaction.atomic():
    # All operations succeed or all fail
    items.update(status='processed')
```

## Edge Cases & Gotchas

### Gotcha 1: Command Name Conflicts
Command names must be unique across all installed apps. If two apps have `myapp/management/commands/import.py`, Django uses the first one found.

**Solution:** Use app-specific prefixes (e.g., `blog_import`, `shop_import`)

### Gotcha 2: Import Order Matters
Commands are discovered when Django loads. Importing models before apps are ready causes `AppRegistryNotReady` errors.

**Solution:** Import models inside `handle()` method, not at module level (if needed before apps ready)

### Gotcha 3: Database Connections in Long-Running Commands
Long-running commands can lose database connections.

**Solution:** Close connections explicitly or use `connection.close_if_unusable_or_obsolete()`

### Gotcha 4: Signal Handlers Still Fire
Signals triggered by ORM operations still run in commands, which can cause unexpected side effects.

**Solution:** Disconnect signals if needed, or use `update()` instead of `save()` to skip signals

## Related Skills

- **django-models**: ORM queries and relationships
- **django-testing**: Testing command behavior
- **django-settings**: Configuration management

## Troubleshooting

### Problem: Command Not Found
```
Unknown command: mycommand
```

**Solutions:**
1. Verify directory structure: `myapp/management/commands/mycommand.py`
2. Check `__init__.py` files exist in `management/` and `commands/`
3. Ensure app is in `INSTALLED_APPS`
4. Try `python manage.py help` to list available commands

### Problem: AppRegistryNotReady
```
django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet
```

**Solutions:**
1. Don't import models at module level
2. Use `django.setup()` if running standalone
3. Import models inside `handle()` method

### Problem: Database Connection Lost
```
OperationalError: MySQL server has gone away
```

**Solutions:**
1. Use `connection.close()` periodically in long loops
2. Call `connection.ensure_connection()` before queries
3. Reduce `CONN_MAX_AGE` for command execution

### Problem: Memory Usage Growing
**Solutions:**
1. Use `.iterator()` for large querysets
2. Call `gc.collect()` periodically
3. Use `only()` and `defer()` to select fewer fields
4. Process in batches and clear Django's query cache

## Examples

See reference files for complete examples:
- [reference/base_classes.md](reference/base_classes.md) - Base class examples
- [reference/arguments.md](reference/arguments.md) - Argument parsing examples
- [reference/output.md](reference/output.md) - Output and styling examples
- [reference/transactions.md](reference/transactions.md) - Database transaction patterns
- [reference/testing.md](reference/testing.md) - Testing examples

## Additional Resources

- Django docs: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
- Use `scripts/generate_command.py` to scaffold new commands
- Check reference files for advanced patterns
