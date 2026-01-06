# Command Base Classes

Django provides three base classes for management commands, each designed for different use cases.

## Table of Contents
- [BaseCommand](#basecommand)
- [AppCommand](#appcommand)
- [LabelCommand](#labelcommand)
- [Comparison Matrix](#comparison-matrix)
- [Advanced Patterns](#advanced-patterns)

## BaseCommand

The most flexible base class for general-purpose commands.

### Basic Structure

```python
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Description shown in help text'

    def add_arguments(self, parser):
        """Define command arguments"""
        pass

    def handle(self, *args, **options):
        """Main command logic"""
        pass
```

### Key Attributes

```python
class Command(BaseCommand):
    # Help text shown in 'python manage.py help mycommand'
    help = 'Command description'

    # Require system checks before running (default: True)
    requires_system_checks = True

    # Specific system check tags to run
    requires_system_checks = ['models', 'database']

    # Require migrations to be up to date (default: False)
    requires_migrations_checks = False

    # Output transaction management messages (default: False)
    output_transaction = False

    # Command can alter data (enables --database option)
    can_import_settings = True

    # Disable colorized output (default: False)
    style = None
```

### Complete Example

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from myapp.models import Article

class Command(BaseCommand):
    help = 'Process articles and update their status'

    def add_arguments(self, parser):
        # Positional argument
        parser.add_argument('status', type=str, choices=['draft', 'published'])

        # Optional arguments
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of articles to process'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Process even if validation fails'
        )

    def handle(self, *args, **options):
        status = options['status']
        limit = options['limit']
        dry_run = options['dry_run']
        force = options['force']

        # Query articles
        articles = Article.objects.filter(status='pending')[:limit]
        total = articles.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('No articles to process'))
            return

        self.stdout.write(f'Found {total} articles to process')

        # Validate unless --force
        if not force:
            invalid = [a for a in articles if not a.is_valid()]
            if invalid:
                raise CommandError(
                    f'{len(invalid)} articles failed validation. '
                    f'Use --force to process anyway.'
                )

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f'Would update {total} articles to status "{status}"'
            ))
            return

        # Process with transaction
        with transaction.atomic():
            updated = 0
            for article in articles:
                article.status = status
                article.save()
                updated += 1

                if options['verbosity'] >= 2:
                    self.stdout.write(f'  Updated article {article.id}')

        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated {updated} articles'
        ))
```

## AppCommand

Specialized for commands that operate on Django apps. Automatically handles app label arguments and validation.

### Basic Structure

```python
from django.core.management.base import AppCommand

class Command(AppCommand):
    help = 'Perform operation on specified apps'

    def add_arguments(self, parser):
        # App labels are automatically added as positional arguments
        super().add_arguments(parser)
        # Add your own arguments here
        parser.add_argument('--option', type=str)

    def handle_app_config(self, app_config, **options):
        """Called once per app label argument"""
        self.stdout.write(f'Processing app: {app_config.label}')
```

### Complete Example: Analyze Models in Apps

```python
from django.core.management.base import AppCommand
from django.apps import apps

class Command(AppCommand):
    help = 'Analyze models in specified Django apps'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--include-abstract',
            action='store_true',
            help='Include abstract models in analysis'
        )
        parser.add_argument(
            '--output-format',
            choices=['text', 'json'],
            default='text',
            help='Output format'
        )

    def handle_app_config(self, app_config, **options):
        """Process each app"""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nApp: {app_config.label}'
        ))

        models = app_config.get_models(
            include_auto_created=False,
            include_swapped=False
        )

        if not options['include_abstract']:
            models = [m for m in models if not m._meta.abstract]

        if not models:
            self.stdout.write('  No models found')
            return

        for model in models:
            self._analyze_model(model, options)

    def _analyze_model(self, model, options):
        """Analyze a single model"""
        meta = model._meta

        # Model info
        self.stdout.write(f'\n  Model: {meta.object_name}')
        self.stdout.write(f'  Table: {meta.db_table}')

        # Count records
        count = model.objects.count()
        self.stdout.write(f'  Records: {count}')

        # Field analysis
        fields = meta.get_fields()
        self.stdout.write(f'  Fields: {len(fields)}')

        if options['verbosity'] >= 2:
            for field in fields:
                field_type = field.__class__.__name__
                self.stdout.write(f'    - {field.name} ({field_type})')

        # Index analysis
        indexes = meta.indexes
        self.stdout.write(f'  Indexes: {len(indexes)}')

        # Constraint analysis
        constraints = meta.constraints
        self.stdout.write(f'  Constraints: {len(constraints)}')
```

### Example: Generate Model Documentation

```python
from django.core.management.base import AppCommand
import json

class Command(AppCommand):
    help = 'Generate documentation for app models'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path'
        )

    def handle_app_config(self, app_config, **options):
        """Document each app's models"""
        models = app_config.get_models()
        docs = {}

        for model in models:
            meta = model._meta
            docs[meta.object_name] = {
                'table': meta.db_table,
                'fields': [
                    {
                        'name': f.name,
                        'type': f.__class__.__name__,
                        'required': not f.null,
                        'help_text': f.help_text or ''
                    }
                    for f in meta.get_fields()
                ],
                'docstring': model.__doc__ or ''
            }

        # Output
        if options['output']:
            with open(options['output'], 'w') as f:
                json.dump(docs, f, indent=2)
            self.stdout.write(self.style.SUCCESS(
                f'Wrote documentation to {options["output"]}'
            ))
        else:
            self.stdout.write(json.dumps(docs, indent=2))
```

## LabelCommand

Specialized for commands that process arbitrary labels (file paths, IDs, names, etc.).

### Basic Structure

```python
from django.core.management.base import LabelCommand

class Command(LabelCommand):
    help = 'Process items by label'
    label = 'label_name'  # Singular form for help text
    missing_args_message = 'Provide at least one label'

    def add_arguments(self, parser):
        # Labels are automatically added as positional arguments
        super().add_arguments(parser)
        # Add your own arguments here

    def handle_label(self, label, **options):
        """Called once per label argument"""
        self.stdout.write(f'Processing: {label}')
```

### Complete Example: Process Files

```python
from django.core.management.base import LabelCommand, CommandError
import os
import json

class Command(LabelCommand):
    help = 'Process JSON files and import data'
    label = 'file path'
    missing_args_message = 'Provide at least one JSON file to process'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate files without importing'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for bulk operations'
        )

    def handle_label(self, label, **options):
        """Process each file"""
        self.stdout.write(f'\nProcessing file: {label}')

        # Validate file exists
        if not os.path.isfile(label):
            raise CommandError(f'File does not exist: {label}')

        # Validate file extension
        if not label.endswith('.json'):
            raise CommandError(f'File must be JSON: {label}')

        # Load and validate JSON
        try:
            with open(label, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in {label}: {e}')

        if not isinstance(data, list):
            raise CommandError(f'JSON must contain an array: {label}')

        self.stdout.write(f'  Found {len(data)} records')

        # Validate structure
        errors = self._validate_records(data)
        if errors:
            self.stderr.write(self.style.ERROR(
                f'  Validation errors: {len(errors)}'
            ))
            for error in errors[:5]:  # Show first 5
                self.stderr.write(f'    - {error}')
            if len(errors) > 5:
                self.stderr.write(f'    ... and {len(errors) - 5} more')
            raise CommandError('Validation failed')

        if options['validate_only']:
            self.stdout.write(self.style.SUCCESS('  Validation passed'))
            return

        # Import data
        imported = self._import_data(data, options['batch_size'])
        self.stdout.write(self.style.SUCCESS(
            f'  Imported {imported} records'
        ))

    def _validate_records(self, data):
        """Validate record structure"""
        errors = []
        required_fields = ['name', 'email']

        for i, record in enumerate(data):
            if not isinstance(record, dict):
                errors.append(f'Record {i}: not a dictionary')
                continue

            for field in required_fields:
                if field not in record:
                    errors.append(f'Record {i}: missing field "{field}"')

            if 'email' in record and '@' not in record['email']:
                errors.append(f'Record {i}: invalid email format')

        return errors

    def _import_data(self, data, batch_size):
        """Import data in batches"""
        from myapp.models import Contact

        batch = []
        imported = 0

        for record in data:
            batch.append(Contact(**record))
            if len(batch) >= batch_size:
                Contact.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
                batch = []

        if batch:
            Contact.objects.bulk_create(batch, ignore_conflicts=True)
            imported += len(batch)

        return imported
```

### Example: Process Model IDs

```python
from django.core.management.base import LabelCommand, CommandError
from myapp.models import Article

class Command(LabelCommand):
    help = 'Publish articles by ID'
    label = 'article ID'
    missing_args_message = 'Provide at least one article ID'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--unpublish',
            action='store_true',
            help='Unpublish instead of publish'
        )

    def handle_label(self, label, **options):
        """Process each article ID"""
        try:
            article_id = int(label)
        except ValueError:
            raise CommandError(f'Invalid article ID: {label}')

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            raise CommandError(f'Article {article_id} does not exist')

        action = 'unpublish' if options['unpublish'] else 'publish'
        article.published = not options['unpublish']
        article.save()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully {action}ed article {article_id}: {article.title}'
        ))
```

## Comparison Matrix

| Feature | BaseCommand | AppCommand | LabelCommand |
|---------|-------------|------------|--------------|
| **Use Case** | General purpose | App-specific operations | Process labels/IDs |
| **Main Method** | `handle()` | `handle_app_config()` | `handle_label()` |
| **Arguments** | Custom | App labels + custom | Labels + custom |
| **Iteration** | Manual | Automatic per app | Automatic per label |
| **Validation** | Custom | App existence | None built-in |
| **Flexibility** | High | Medium | Medium |
| **Boilerplate** | More | Less | Less |

### When to Use Each

**Use BaseCommand when:**
- Command doesn't fit app or label patterns
- Need full control over arguments and flow
- Complex multi-step operations
- No natural iteration pattern
- Custom validation requirements

**Use AppCommand when:**
- Operating on Django apps (inspecting, analyzing, generating)
- Need to process models in specific apps
- Working with app configurations
- Generating app-specific artifacts

**Use LabelCommand when:**
- Processing files, IDs, or names
- Simple iteration over string inputs
- Each label is independent
- Similar processing per label

## Advanced Patterns

### Mixing Base Classes with Custom Logic

```python
from django.core.management.base import BaseCommand, CommandParser

class Command(BaseCommand):
    help = 'Complex command with subcommands'

    def create_parser(self, prog_name, subcommand, **kwargs):
        """Customize parser for complex argument handling"""
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        return parser

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='Available subcommands'
        )

        # Subcommand: import
        import_parser = subparsers.add_parser('import', help='Import data')
        import_parser.add_argument('file', type=str)

        # Subcommand: export
        export_parser = subparsers.add_parser('export', help='Export data')
        export_parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        subcommand = options.get('subcommand')

        if subcommand == 'import':
            self.handle_import(options)
        elif subcommand == 'export':
            self.handle_export(options)
        else:
            self.print_help('manage.py', 'mycommand')

    def handle_import(self, options):
        self.stdout.write(f'Importing from {options["file"]}')

    def handle_export(self, options):
        self.stdout.write(f'Exporting to {options["file"]}')
```

### Async Command Support

Django 4.1+ supports async commands:

```python
from django.core.management.base import BaseCommand
import asyncio

class Command(BaseCommand):
    help = 'Async command example'

    async def handle_async(self, *args, **options):
        """Async version of handle()"""
        await self.process_data()
        self.stdout.write(self.style.SUCCESS('Done'))

    async def process_data(self):
        # Async operations
        await asyncio.sleep(1)

    def handle(self, *args, **options):
        """Sync wrapper that calls async version"""
        asyncio.run(self.handle_async(*args, **options))
```

### Multi-Database Support

```python
from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    help = 'Multi-database operation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default='default',
            help='Database to use'
        )

    def handle(self, *args, **options):
        database = options['database']

        # Validate database exists
        if database not in connections:
            raise CommandError(f'Database "{database}" not configured')

        # Use specific database
        from myapp.models import MyModel
        items = MyModel.objects.using(database).all()

        self.stdout.write(f'Found {items.count()} items in {database}')
```

### Progress Reporting with tqdm

```python
from django.core.management.base import BaseCommand
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Process items with progress bar'

    def handle(self, *args, **options):
        from myapp.models import Item

        items = Item.objects.all()
        total = items.count()

        # Progress bar
        for item in tqdm(items.iterator(), total=total, desc='Processing'):
            self.process_item(item)

        self.stdout.write(self.style.SUCCESS('Complete'))

    def process_item(self, item):
        # Processing logic
        pass
```

### Cron-Friendly Commands

```python
from django.core.management.base import BaseCommand
import sys
import logging

class Command(BaseCommand):
    help = 'Cron-friendly command with logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (for cron)'
        )

    def handle(self, *args, **options):
        # Configure logging for cron
        if options['quiet']:
            self.stdout = open('/dev/null', 'w')
            logging.basicConfig(
                filename='/var/log/myapp/command.log',
                level=logging.INFO
            )

        try:
            self.do_work()
            sys.exit(0)  # Success exit code
        except Exception as e:
            logging.error(f'Command failed: {e}')
            sys.exit(1)  # Failure exit code

    def do_work(self):
        self.stdout.write('Working...')
        # Command logic
```

## Best Practices

1. **Choose the right base class** - Don't use BaseCommand when AppCommand or LabelCommand fits
2. **Set helpful attributes** - Always set `help`, consider `requires_system_checks`
3. **Validate early** - Check arguments before processing
4. **Use transactions** - Wrap database operations in `transaction.atomic()`
5. **Support dry-run** - Add `--dry-run` for destructive operations
6. **Handle errors gracefully** - Raise `CommandError` for user errors
7. **Log appropriately** - Use `self.stdout` for success, `self.stderr` for errors
8. **Test thoroughly** - Write tests using `call_command()`
9. **Document well** - Clear help text and argument descriptions
10. **Consider performance** - Use `.iterator()` for large querysets
