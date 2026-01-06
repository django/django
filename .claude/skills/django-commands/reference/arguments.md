# Command Arguments

This reference covers argument handling in Django management commands using `argparse`.

## Table of Contents
- [Basic Argument Syntax](#basic-argument-syntax)
- [Positional Arguments](#positional-arguments)
- [Optional Arguments](#optional-arguments)
- [Argument Types](#argument-types)
- [Validation](#validation)
- [Advanced Patterns](#advanced-patterns)

## Basic Argument Syntax

Override the `add_arguments()` method to define command arguments:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def add_arguments(self, parser):
        # parser is an argparse.ArgumentParser instance
        parser.add_argument('name', type=str, help='Item name')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **options):
        # Access via options dictionary
        name = options['name']
        verbose = options['verbose']
```

## Positional Arguments

Required arguments that must be provided in order.

### Single Positional Argument

```python
def add_arguments(self, parser):
    parser.add_argument('username', type=str, help='Username to process')

# Usage: python manage.py mycommand john
```

### Multiple Positional Arguments

```python
def add_arguments(self, parser):
    parser.add_argument('source', type=str, help='Source file')
    parser.add_argument('destination', type=str, help='Destination file')

# Usage: python manage.py mycommand input.csv output.csv
```

### Variable Number of Arguments

```python
def add_arguments(self, parser):
    parser.add_argument(
        'files',
        nargs='+',  # One or more
        type=str,
        help='Files to process'
    )

def handle(self, *args, **options):
    files = options['files']  # List of file paths
    for file_path in files:
        self.stdout.write(f'Processing {file_path}')

# Usage: python manage.py mycommand file1.txt file2.txt file3.txt
```

### Optional Positional Arguments

```python
def add_arguments(self, parser):
    parser.add_argument(
        'files',
        nargs='*',  # Zero or more
        type=str,
        help='Files to process (optional)'
    )

# Usage: python manage.py mycommand
#    or: python manage.py mycommand file1.txt file2.txt
```

### `nargs` Options

| Value | Description | Example |
|-------|-------------|---------|
| `N` (int) | Exactly N arguments | `nargs=3` requires 3 args |
| `'?'` | 0 or 1 argument | Optional single arg |
| `'*'` | 0 or more arguments | Optional list |
| `'+'` | 1 or more arguments | Required list |

```python
# Exactly 2 arguments
parser.add_argument('coordinates', nargs=2, type=float)
# Usage: mycommand 10.5 20.3
# Result: options['coordinates'] = [10.5, 20.3]

# Optional single argument with default
parser.add_argument('config', nargs='?', default='config.json')
# Usage: mycommand
# Result: options['config'] = 'config.json'
# Usage: mycommand custom.json
# Result: options['config'] = 'custom.json'
```

## Optional Arguments

Optional flags and arguments with `--` prefix.

### Boolean Flags

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

def handle(self, *args, **options):
    if options['dry_run']:
        self.stdout.write('DRY RUN MODE')

# Usage: python manage.py mycommand --dry-run
```

### Store False (Inverse Flags)

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--no-backup',
        action='store_false',
        dest='backup',  # Stored as options['backup']
        help='Skip creating backup'
    )

def handle(self, *args, **options):
    if options['backup']:  # True by default, False if --no-backup
        self.create_backup()

# Usage: python manage.py mycommand --no-backup
```

### Optional Arguments with Values

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum items to process (default: 100)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path'
    )

def handle(self, *args, **options):
    limit = options['limit']  # 100 if not provided
    output = options['output']  # None if not provided

# Usage: python manage.py mycommand --limit 500 --output results.txt
```

### Required Optional Arguments

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Configuration file (required)'
    )

# Usage: python manage.py mycommand --config settings.json
```

### Short and Long Forms

```python
def add_arguments(self, parser):
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file'
    )

# Usage: python manage.py mycommand -v -o output.txt
#    or: python manage.py mycommand --verbose --output output.txt
```

## Argument Types

### Built-in Types

```python
def add_arguments(self, parser):
    parser.add_argument('--count', type=int)
    parser.add_argument('--price', type=float)
    parser.add_argument('--name', type=str)  # Default type
    parser.add_argument('--data', type=bytes)
```

### File Objects

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--input',
        type=argparse.FileType('r'),
        help='Input file (opened for reading)'
    )
    parser.add_argument(
        '--output',
        type=argparse.FileType('w'),
        help='Output file (opened for writing)'
    )

def handle(self, *args, **options):
    if options['input']:
        data = options['input'].read()
        options['input'].close()

    if options['output']:
        options['output'].write('result')
        options['output'].close()
```

### Custom Type Functions

```python
import os
from django.core.management.base import CommandError

def valid_file_path(path):
    """Custom type validator for file paths"""
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f'File does not exist: {path}')
    return path

def valid_date(date_string):
    """Custom type validator for dates"""
    from datetime import datetime
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f'Invalid date format: {date_string}. Use YYYY-MM-DD'
        )

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=valid_file_path,
            help='Existing file path'
        )
        parser.add_argument(
            '--start-date',
            type=valid_date,
            help='Start date (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        file_path = options['file']  # Validated file path
        start_date = options['start_date']  # datetime.date object
```

### Choices (Enum Values)

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'csv', 'xml'],
        default='json',
        help='Output format'
    )
    parser.add_argument(
        '--level',
        type=int,
        choices=[1, 2, 3],
        help='Processing level'
    )

# Usage: python manage.py mycommand --format csv
# Error if: python manage.py mycommand --format pdf
```

### Path Arguments

```python
from pathlib import Path

def add_arguments(self, parser):
    parser.add_argument(
        '--directory',
        type=Path,
        help='Directory path as Path object'
    )

def handle(self, *args, **options):
    directory = options['directory']  # pathlib.Path object
    if directory and directory.is_dir():
        for file in directory.iterdir():
            self.stdout.write(f'Found: {file}')
```

## Validation

### Using `choices`

```python
def add_arguments(self, parser):
    parser.add_argument(
        'action',
        choices=['create', 'update', 'delete'],
        help='Action to perform'
    )
```

### Custom Validation in `handle()`

```python
from django.core.management.base import CommandError

def handle(self, *args, **options):
    limit = options['limit']

    # Validate range
    if limit < 1 or limit > 10000:
        raise CommandError('Limit must be between 1 and 10000')

    # Validate file existence
    file_path = options['file']
    if not os.path.exists(file_path):
        raise CommandError(f'File not found: {file_path}')

    # Validate mutually exclusive options
    if options['create'] and options['update']:
        raise CommandError('Cannot use --create and --update together')
```

### Mutually Exclusive Groups

```python
def add_arguments(self, parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--create', action='store_true')
    group.add_argument('--update', action='store_true')
    group.add_argument('--delete', action='store_true')

# Valid: python manage.py mycommand --create
# Invalid: python manage.py mycommand --create --update
```

### Dependent Arguments

```python
def add_arguments(self, parser):
    parser.add_argument('--import', action='store_true', dest='do_import')
    parser.add_argument('--file', type=str, help='File to import')

def handle(self, *args, **options):
    if options['do_import'] and not options['file']:
        raise CommandError('--file is required when using --import')
```

### Argument Groups (Visual Grouping)

```python
def add_arguments(self, parser):
    # Input options
    input_group = parser.add_argument_group('input options')
    input_group.add_argument('--input', type=str)
    input_group.add_argument('--format', choices=['json', 'csv'])

    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument('--output', type=str)
    output_group.add_argument('--compress', action='store_true')

    # Processing options
    proc_group = parser.add_argument_group('processing options')
    proc_group.add_argument('--batch-size', type=int, default=1000)
    proc_group.add_argument('--parallel', action='store_true')
```

## Advanced Patterns

### Subcommands

```python
def add_arguments(self, parser):
    subparsers = parser.add_subparsers(
        dest='subcommand',
        help='Available subcommands',
        required=True
    )

    # Import subcommand
    import_parser = subparsers.add_parser(
        'import',
        help='Import data from file'
    )
    import_parser.add_argument('file', type=str)
    import_parser.add_argument('--format', choices=['json', 'csv'])

    # Export subcommand
    export_parser = subparsers.add_parser(
        'export',
        help='Export data to file'
    )
    export_parser.add_argument('file', type=str)
    export_parser.add_argument('--all', action='store_true')

def handle(self, *args, **options):
    subcommand = options['subcommand']

    if subcommand == 'import':
        self.handle_import(options)
    elif subcommand == 'export':
        self.handle_export(options)

# Usage: python manage.py mycommand import data.json --format json
#        python manage.py mycommand export output.json --all
```

### Environment Variable Defaults

```python
import os

def add_arguments(self, parser):
    parser.add_argument(
        '--api-key',
        type=str,
        default=os.environ.get('API_KEY'),
        help='API key (or set API_KEY environment variable)'
    )
    parser.add_argument(
        '--database',
        type=str,
        default=os.environ.get('DATABASE_URL', 'default'),
        help='Database connection'
    )
```

### Config File Arguments

```python
import json

def add_arguments(self, parser):
    parser.add_argument(
        '--config',
        type=str,
        help='JSON config file'
    )
    parser.add_argument('--option1', type=str)
    parser.add_argument('--option2', type=int)

def handle(self, *args, **options):
    # Load config file if provided
    if options['config']:
        with open(options['config'], 'r') as f:
            config = json.load(f)

        # Merge with command-line options (CLI takes precedence)
        for key, value in config.items():
            if key not in options or options[key] is None:
                options[key] = value

    # Use merged options
    option1 = options['option1']
    option2 = options['option2']
```

### Dynamic Default Values

```python
from django.utils import timezone

def add_arguments(self, parser):
    parser.add_argument(
        '--date',
        type=str,
        help='Date to process (default: today)'
    )

def handle(self, *args, **options):
    # Set default in handle() for dynamic values
    date = options['date'] or timezone.now().date().isoformat()
    self.stdout.write(f'Processing date: {date}')
```

### Count Actions

```python
def add_arguments(self, parser):
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (can be used multiple times)'
    )

def handle(self, *args, **options):
    verbosity = options['verbose']

    if verbosity >= 2:
        self.stdout.write('DEBUG: Detailed output')
    elif verbosity >= 1:
        self.stdout.write('INFO: Normal output')

# Usage: python manage.py mycommand -v      # verbosity = 1
#        python manage.py mycommand -vv     # verbosity = 2
#        python manage.py mycommand -vvv    # verbosity = 3
```

### Append Actions (List Building)

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--include',
        action='append',
        help='Include pattern (can be used multiple times)'
    )
    parser.add_argument(
        '--exclude',
        action='append',
        help='Exclude pattern (can be used multiple times)'
    )

def handle(self, *args, **options):
    include = options['include'] or []  # List of patterns
    exclude = options['exclude'] or []

# Usage: python manage.py mycommand --include "*.py" --include "*.js" --exclude "test_*"
# Result: options['include'] = ['*.py', '*.js']
#         options['exclude'] = ['test_*']
```

### Store Constant Actions

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--debug',
        action='store_const',
        const=True,
        default=False,
        help='Enable debug mode'
    )

    parser.add_argument(
        '--level',
        action='store_const',
        const='advanced',
        default='basic',
        help='Use advanced level'
    )
```

### Metavar (Custom Display Names)

```python
def add_arguments(self, parser):
    parser.add_argument(
        'source',
        metavar='SOURCE_FILE',
        help='Source file path'
    )
    parser.add_argument(
        '--output',
        metavar='DEST',
        help='Destination path'
    )

# Help text shows:
# usage: manage.py mycommand SOURCE_FILE [--output DEST]
```

## Complete Real-World Example

```python
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import os

class Command(BaseCommand):
    help = 'Import user data from various file formats'

    def add_arguments(self, parser):
        # Positional: input files
        parser.add_argument(
            'files',
            nargs='+',
            type=str,
            help='Input files to process'
        )

        # Format group
        format_group = parser.add_mutually_exclusive_group()
        format_group.add_argument(
            '--csv',
            action='store_const',
            const='csv',
            dest='format',
            help='Process as CSV files'
        )
        format_group.add_argument(
            '--json',
            action='store_const',
            const='json',
            dest='format',
            help='Process as JSON files'
        )

        # Processing options
        proc_group = parser.add_argument_group('processing options')
        proc_group.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Records per batch (default: 1000)'
        )
        proc_group.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continue processing on errors'
        )

        # Output options
        output_group = parser.add_argument_group('output options')
        output_group.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate without importing'
        )
        output_group.add_argument(
            '--log-file',
            type=str,
            help='Write log to file'
        )

        # Database options
        parser.add_argument(
            '--database',
            default='default',
            help='Target database (default: default)'
        )

    def handle(self, *args, **options):
        # Extract options
        files = options['files']
        file_format = options.get('format')
        batch_size = options['batch_size']
        skip_errors = options['skip_errors']
        dry_run = options['dry_run']
        database = options['database']

        # Validate batch size
        if batch_size < 1 or batch_size > 10000:
            raise CommandError('Batch size must be between 1 and 10000')

        # Auto-detect format if not specified
        if not file_format:
            first_file = files[0]
            if first_file.endswith('.csv'):
                file_format = 'csv'
            elif first_file.endswith('.json'):
                file_format = 'json'
            else:
                raise CommandError(
                    'Cannot detect format. Use --csv or --json'
                )

        # Validate all files exist
        for file_path in files:
            if not os.path.isfile(file_path):
                raise CommandError(f'File not found: {file_path}')

        # Process files
        total_imported = 0
        total_errors = 0

        for file_path in files:
            self.stdout.write(f'\nProcessing: {file_path}')

            try:
                imported, errors = self.process_file(
                    file_path,
                    file_format,
                    batch_size,
                    dry_run,
                    database
                )
                total_imported += imported
                total_errors += errors

                self.stdout.write(self.style.SUCCESS(
                    f'  Imported: {imported}, Errors: {errors}'
                ))

            except Exception as e:
                total_errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  Failed: {e}'
                ))
                if not skip_errors:
                    raise

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'Total imported: {total_imported}')
        self.stdout.write(f'Total errors: {total_errors}')

        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN - No changes made'))

    def process_file(self, file_path, file_format, batch_size, dry_run, database):
        """Process a single file"""
        # Implementation details...
        return 100, 0  # imported, errors
```

## Best Practices

1. **Provide clear help text** - Use `help` parameter for all arguments
2. **Set sensible defaults** - Use `default` parameter where appropriate
3. **Validate early** - Check arguments at the start of `handle()`
4. **Use type converters** - Leverage `type` parameter for automatic conversion
5. **Group related arguments** - Use `add_argument_group()` for clarity
6. **Support --dry-run** - Always add for destructive operations
7. **Use choices for enums** - Restrict to valid values with `choices`
8. **Document in help** - Show defaults and valid ranges in help text
9. **Handle errors gracefully** - Raise `CommandError` with clear messages
10. **Test argument parsing** - Verify all combinations work correctly
