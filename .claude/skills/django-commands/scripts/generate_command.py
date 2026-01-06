#!/usr/bin/env python3
"""
Django Management Command Generator

Generates boilerplate for Django management commands with different patterns.

Usage:
    python generate_command.py <app_name> <command_name> [options]

Examples:
    # Basic command
    python generate_command.py myapp process_data --type base

    # Import command
    python generate_command.py myapp import_users --type import --description "Import users from CSV"

    # Maintenance command
    python generate_command.py myapp cleanup_old_data --type maintenance

    # Report command
    python generate_command.py myapp generate_report --type report

    # Integration command
    python generate_command.py myapp sync_external_api --type integration
"""

import os
import sys
import argparse
from pathlib import Path


TEMPLATES = {
    'base': '''from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = '{description}'

    def add_arguments(self, parser):
        parser.add_argument(
            'items',
            nargs='+',
            type=str,
            help='Items to process'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum items to process (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them'
        )

    def handle(self, *args, **options):
        items = options['items']
        limit = options['limit']
        dry_run = options['dry_run']
        verbosity = options['verbosity']

        if verbosity >= 1:
            self.stdout.write(f'Processing {{len(items)}} items (limit: {{limit}})')

        processed = 0
        for item in items[:limit]:
            if dry_run:
                self.stdout.write(f'Would process: {{item}}')
            else:
                self.process_item(item)

            processed += 1

            if verbosity >= 2:
                self.stdout.write(f'  Processed {{processed}}/{{len(items)}}')

        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN: No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully processed {{processed}} items'
            ))

    def process_item(self, item):
        """Process a single item"""
        # TODO: Implement processing logic
        pass
''',

    'import': '''import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from myapp.models import MyModel  # TODO: Update import


class Command(BaseCommand):
    help = '{description}'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='CSV file to import'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Records per batch (default: 1000)'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continue processing on errors'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate without importing'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        skip_errors = options['skip_errors']
        dry_run = options['dry_run']
        verbosity = options['verbosity']

        # Validate file exists
        if not os.path.isfile(csv_file):
            raise CommandError(f'File not found: {{csv_file}}')

        # Load and validate data
        self.stdout.write('Loading data...')
        data, errors = self.load_csv(csv_file, skip_errors)

        self.stdout.write(f'Loaded {{len(data)}} valid records')
        if errors:
            self.stderr.write(self.style.WARNING(
                f'{{len(errors)}} records had errors'
            ))

        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN: No data imported'))
            return

        # Import in batches
        self.stdout.write('Importing...')
        imported = self.import_data(data, batch_size, verbosity)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully imported {{imported}} records'
        ))

    def load_csv(self, csv_file, skip_errors):
        """Load and validate CSV data"""
        data = []
        errors = []

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader, 1):
                try:
                    # TODO: Validate row data
                    validated = self.validate_row(row)
                    data.append(validated)
                except Exception as e:
                    errors.append((i, str(e)))
                    if not skip_errors:
                        raise CommandError(
                            f'Row {{i}} validation failed: {{e}}'
                        )

        return data, errors

    def validate_row(self, row):
        """Validate and transform a CSV row"""
        # TODO: Implement validation logic
        return row

    def import_data(self, data, batch_size, verbosity):
        """Import data in batches"""
        batch = []
        imported = 0

        for record in data:
            batch.append(MyModel(**record))  # TODO: Update model

            if len(batch) >= batch_size:
                with transaction.atomic():
                    MyModel.objects.bulk_create(batch)  # TODO: Update model
                    imported += len(batch)

                if verbosity >= 1:
                    self.stdout.write(f'  Imported {{imported}} records...')

                batch = []

        # Import remaining records
        if batch:
            with transaction.atomic():
                MyModel.objects.bulk_create(batch)  # TODO: Update model
                imported += len(batch)

        return imported
''',

    'maintenance': '''from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from myapp.models import MyModel  # TODO: Update import


class Command(BaseCommand):
    help = '{description}'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete records older than N days (default: 30)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Records per batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without deleting'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        no_input = options['no_input']
        verbosity = options['verbosity']

        # Calculate cutoff date
        cutoff = timezone.now() - timedelta(days=days)

        # Find records to delete
        items = MyModel.objects.filter(created_at__lt=cutoff)  # TODO: Update query
        count = items.count()

        if count == 0:
            self.stdout.write('No records to delete')
            return

        # Show what will be deleted
        self.stdout.write(f'Found {{count}} records older than {{days}} days')

        if verbosity >= 2:
            for item in items[:5]:
                self.stdout.write(f'  - {{item}}')
            if count > 5:
                self.stdout.write(f'  ... and {{count - 5}} more')

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f'DRY RUN: Would delete {{count}} records'
            ))
            return

        # Confirm deletion
        if not no_input:
            confirm = input(f'\\nDelete {{count}} records? Type "yes" to continue: ')
            if confirm != 'yes':
                self.stdout.write('Cancelled')
                return

        # Delete in batches
        self.stdout.write('Deleting records...')
        total_deleted = self.delete_in_batches(items, batch_size, verbosity)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {{total_deleted}} records'
        ))

    def delete_in_batches(self, queryset, batch_size, verbosity):
        """Delete records in batches"""
        total_deleted = 0

        while True:
            # Get batch of IDs
            ids = list(
                queryset.values_list('id', flat=True)[:batch_size]
            )

            if not ids:
                break

            # Delete batch
            with transaction.atomic():
                deleted, _ = MyModel.objects.filter(id__in=ids).delete()  # TODO: Update model
                total_deleted += deleted

            if verbosity >= 1:
                self.stdout.write(f'  Deleted {{total_deleted}} records...')

        return total_deleted
''',

    'report': '''from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum, Avg
from django.utils import timezone
import json
from myapp.models import MyModel  # TODO: Update import


class Command(BaseCommand):
    help = '{description}'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['text', 'json', 'csv'],
            default='text',
            help='Output format (default: text)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file (default: stdout)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Report period in days (default: 7)'
        )

    def handle(self, *args, **options):
        output_format = options['format']
        output_file = options['output']
        days = options['days']

        # Generate report data
        self.stdout.write('Generating report...')
        report_data = self.generate_report(days)

        # Format output
        if output_format == 'text':
            output = self.format_text(report_data)
        elif output_format == 'json':
            output = self.format_json(report_data)
        elif output_format == 'csv':
            output = self.format_csv(report_data)

        # Write output
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(
                f'Report written to {{output_file}}'
            ))
        else:
            self.stdout.write(output)

    def generate_report(self, days):
        """Generate report data"""
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)

        # TODO: Customize report queries
        stats = MyModel.objects.filter(created_at__gte=cutoff).aggregate(
            total=Count('id'),
            # Add more aggregations as needed
        )

        # Breakdown by category
        by_status = MyModel.objects.filter(
            created_at__gte=cutoff
        ).values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        return {{
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'summary': stats,
            'by_status': list(by_status),
        }}

    def format_text(self, data):
        """Format report as text"""
        lines = []
        lines.append('=' * 60)
        lines.append('Report')
        lines.append('=' * 60)
        lines.append(f"Period: {{data['period_days']}} days")
        lines.append(f"Generated: {{data['generated_at']}}")
        lines.append('')

        lines.append('Summary:')
        for key, value in data['summary'].items():
            lines.append(f'  {{key}}: {{value}}')
        lines.append('')

        lines.append('By Status:')
        for item in data['by_status']:
            lines.append(f"  {{item['status']}}: {{item['count']}}")

        lines.append('=' * 60)
        return '\\n'.join(lines)

    def format_json(self, data):
        """Format report as JSON"""
        return json.dumps(data, indent=2)

    def format_csv(self, data):
        """Format report as CSV"""
        lines = []
        lines.append('status,count')
        for item in data['by_status']:
            lines.append(f"{{item['status']}},{{item['count']}}")
        return '\\n'.join(lines)
''',

    'integration': '''import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from myapp.models import MyModel  # TODO: Update import


class Command(BaseCommand):
    help = '{description}'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default=getattr(settings, 'EXTERNAL_API_URL', None),
            help='External API URL'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Records per batch (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without syncing'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if unchanged'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']
        verbosity = options['verbosity']

        if not api_url:
            raise CommandError('API URL not configured')

        # Fetch data from external API
        self.stdout.write('Fetching data from external API...')
        try:
            external_data = self.fetch_external_data(api_url)
        except Exception as e:
            raise CommandError(f'Failed to fetch data: {{e}}')

        self.stdout.write(f'Fetched {{len(external_data)}} records')

        # Compare with local data
        self.stdout.write('Comparing with local data...')
        to_create, to_update = self.compare_data(external_data, force)

        self.stdout.write(f'To create: {{len(to_create)}}')
        self.stdout.write(f'To update: {{len(to_update)}}')

        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN: No changes made'))
            return

        # Sync data
        self.stdout.write('Syncing data...')
        created, updated = self.sync_data(
            to_create, to_update, batch_size, verbosity
        )

        self.stdout.write(self.style.SUCCESS(
            f'Synced successfully: {{created}} created, {{updated}} updated'
        ))

    def fetch_external_data(self, api_url):
        """Fetch data from external API"""
        # TODO: Add authentication headers if needed
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        return response.json()

    def compare_data(self, external_data, force):
        """Compare external data with local data"""
        to_create = []
        to_update = []

        for item in external_data:
            external_id = item.get('id')

            try:
                local_obj = MyModel.objects.get(external_id=external_id)  # TODO: Update

                # Check if update needed
                if force or self.needs_update(local_obj, item):
                    to_update.append((local_obj, item))

            except MyModel.DoesNotExist:
                to_create.append(item)

        return to_create, to_update

    def needs_update(self, local_obj, external_data):
        """Check if local object needs update"""
        # TODO: Implement comparison logic
        return True

    def sync_data(self, to_create, to_update, batch_size, verbosity):
        """Sync data to local database"""
        created = 0
        updated = 0

        # Create new records
        if to_create:
            batch = []
            for item in to_create:
                batch.append(MyModel(**self.transform_data(item)))  # TODO: Update

                if len(batch) >= batch_size:
                    with transaction.atomic():
                        MyModel.objects.bulk_create(batch)  # TODO: Update
                        created += len(batch)

                    if verbosity >= 1:
                        self.stdout.write(f'  Created {{created}} records...')

                    batch = []

            if batch:
                with transaction.atomic():
                    MyModel.objects.bulk_create(batch)  # TODO: Update
                    created += len(batch)

        # Update existing records
        for local_obj, external_data in to_update:
            self.update_object(local_obj, external_data)
            local_obj.save()
            updated += 1

            if verbosity >= 2:
                self.stdout.write(f'  Updated: {{local_obj}}')

        return created, updated

    def transform_data(self, external_data):
        """Transform external data to local model fields"""
        # TODO: Implement data transformation
        return {{
            'external_id': external_data.get('id'),
            # Map other fields
        }}

    def update_object(self, obj, external_data):
        """Update local object with external data"""
        # TODO: Implement update logic
        transformed = self.transform_data(external_data)
        for key, value in transformed.items():
            setattr(obj, key, value)
''',
}


def generate_command(app_name, command_name, command_type, description, output_dir=None):
    """Generate command file"""
    # Determine output directory
    if output_dir:
        command_dir = Path(output_dir)
    else:
        command_dir = Path(app_name) / 'management' / 'commands'

    # Create directories
    management_dir = command_dir.parent
    management_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py files
    (management_dir.parent / '__init__.py').touch()
    (management_dir / '__init__.py').touch()
    command_dir.mkdir(exist_ok=True)
    (command_dir / '__init__.py').touch()

    # Generate command file
    command_file = command_dir / f'{command_name}.py'

    if command_file.exists():
        print(f'Error: Command file already exists: {command_file}')
        return False

    # Get template
    template = TEMPLATES.get(command_type)
    if not template:
        print(f'Error: Unknown command type: {command_type}')
        print(f'Available types: {", ".join(TEMPLATES.keys())}')
        return False

    # Format template
    content = template.format(description=description)

    # Write file
    command_file.write_text(content)

    print(f'Successfully created command: {command_file}')
    print(f'\nNext steps:')
    print(f'1. Edit {command_file}')
    print(f'2. Update model imports and queries (search for TODO)')
    print(f'3. Test with: python manage.py {command_name} --help')
    print(f'4. Write tests in tests/test_commands.py')

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate Django management command boilerplate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'app_name',
        help='Django app name (e.g., myapp)'
    )
    parser.add_argument(
        'command_name',
        help='Command name (e.g., import_users)'
    )
    parser.add_argument(
        '--type',
        choices=list(TEMPLATES.keys()),
        default='base',
        help='Command type (default: base)'
    )
    parser.add_argument(
        '--description',
        type=str,
        default='Command description',
        help='Command help text'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (default: <app_name>/management/commands)'
    )

    args = parser.parse_args()

    success = generate_command(
        args.app_name,
        args.command_name,
        args.type,
        args.description,
        args.output_dir
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
