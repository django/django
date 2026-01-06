#!/usr/bin/env python3
"""
Django Model Generator Script

Generates Django model code from a JSON schema definition.

Usage:
    python generate_model.py schema.json
    python generate_model.py schema.json > models.py

Input Format (JSON):
{
  "model_name": "Article",
  "app_label": "blog",
  "fields": [
    {
      "name": "title",
      "type": "CharField",
      "options": {"max_length": 200}
    },
    {
      "name": "author",
      "type": "ForeignKey",
      "options": {
        "to": "auth.User",
        "on_delete": "CASCADE",
        "related_name": "articles"
      }
    }
  ],
  "meta": {
    "verbose_name": "Article",
    "verbose_name_plural": "Articles",
    "ordering": ["-created_at"]
  }
}
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


# Valid Django field types
VALID_FIELD_TYPES = {
    'AutoField', 'BigAutoField', 'BigIntegerField', 'BinaryField',
    'BooleanField', 'CharField', 'DateField', 'DateTimeField',
    'DecimalField', 'DurationField', 'EmailField', 'FileField',
    'FilePathField', 'FloatField', 'ImageField', 'IntegerField',
    'GenericIPAddressField', 'JSONField', 'PositiveBigIntegerField',
    'PositiveIntegerField', 'PositiveSmallIntegerField', 'SlugField',
    'SmallIntegerField', 'TextField', 'TimeField', 'URLField',
    'UUIDField', 'ForeignKey', 'ManyToManyField', 'OneToOneField',
}

# Fields that require imports
IMPORT_REQUIREMENTS = {
    'UUIDField': ['import uuid'],
    'JSONField': [],  # Built-in since Django 3.1
}

# on_delete options for relationship fields
ON_DELETE_OPTIONS = {
    'CASCADE', 'PROTECT', 'SET_NULL', 'SET_DEFAULT', 'SET', 'DO_NOTHING'
}


class ModelGenerator:
    """Generate Django model code from schema"""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.imports = set()
        self.errors = []

    def validate_schema(self) -> bool:
        """Validate the schema"""
        if 'model_name' not in self.schema:
            self.errors.append("Missing required field: model_name")
            return False

        if 'fields' not in self.schema or not isinstance(self.schema['fields'], list):
            self.errors.append("Missing or invalid 'fields' list")
            return False

        # Validate each field
        for i, field in enumerate(self.schema['fields']):
            if 'name' not in field:
                self.errors.append(f"Field {i}: Missing 'name'")
                return False

            if 'type' not in field:
                self.errors.append(f"Field {i} ({field['name']}): Missing 'type'")
                return False

            if field['type'] not in VALID_FIELD_TYPES:
                self.errors.append(
                    f"Field {i} ({field['name']}): Invalid type '{field['type']}'"
                )
                return False

            # Validate relationship fields
            if field['type'] in {'ForeignKey', 'ManyToManyField', 'OneToOneField'}:
                options = field.get('options', {})
                if 'to' not in options:
                    self.errors.append(
                        f"Field {field['name']}: Relationship field requires 'to' option"
                    )
                    return False

                if field['type'] in {'ForeignKey', 'OneToOneField'}:
                    if 'on_delete' not in options:
                        self.errors.append(
                            f"Field {field['name']}: {field['type']} requires 'on_delete' option"
                        )
                        return False

        return True

    def generate(self) -> str:
        """Generate model code"""
        if not self.validate_schema():
            raise ValueError(f"Schema validation failed: {', '.join(self.errors)}")

        lines = []

        # Add imports
        self._add_standard_imports()
        lines.extend(sorted(self.imports))
        lines.append('')
        lines.append('')

        # Generate model class
        model_name = self.schema['model_name']
        lines.append(f"class {model_name}(models.Model):")

        # Add docstring if provided
        if 'description' in self.schema:
            lines.append(f'    """{self.schema["description"]}"""')
            lines.append('')

        # Generate fields
        field_lines = self._generate_fields()
        if field_lines:
            lines.extend(field_lines)
        else:
            lines.append('    pass')

        # Add Meta class if provided
        if 'meta' in self.schema:
            lines.append('')
            lines.extend(self._generate_meta())

        # Add __str__ method if specified or default
        lines.append('')
        lines.extend(self._generate_str_method())

        # Add custom methods if provided
        if 'methods' in self.schema:
            lines.append('')
            lines.extend(self._generate_methods())

        return '\n'.join(lines)

    def _add_standard_imports(self):
        """Add standard Django imports"""
        self.imports.add('from django.db import models')

        # Add imports based on field types
        for field in self.schema['fields']:
            field_type = field['type']
            if field_type in IMPORT_REQUIREMENTS:
                for imp in IMPORT_REQUIREMENTS[field_type]:
                    self.imports.add(imp)

            # Check for UUIDField with uuid.uuid4 default
            if field_type == 'UUIDField':
                options = field.get('options', {})
                if 'default' in options and 'uuid4' in str(options['default']):
                    self.imports.add('import uuid')

    def _generate_fields(self) -> List[str]:
        """Generate field definitions"""
        lines = []

        for field in self.schema['fields']:
            field_line = self._generate_field(field)
            lines.append(f"    {field_line}")

        return lines

    def _generate_field(self, field: Dict[str, Any]) -> str:
        """Generate a single field definition"""
        name = field['name']
        field_type = field['type']
        options = field.get('options', {})

        # Build field definition
        parts = [f"{name} = models.{field_type}("]

        # Handle relationship fields specially
        if field_type in {'ForeignKey', 'ManyToManyField', 'OneToOneField'}:
            args = self._generate_relationship_args(field_type, options)
        else:
            args = self._generate_field_args(field_type, options)

        parts.append(args)
        parts.append(')')

        return ''.join(parts)

    def _generate_relationship_args(
        self,
        field_type: str,
        options: Dict[str, Any]
    ) -> str:
        """Generate arguments for relationship fields"""
        args = []

        # 'to' argument (positional)
        to_model = options.pop('to')
        args.append(f"'{to_model}'")

        # on_delete argument (required for FK and O2O)
        if field_type in {'ForeignKey', 'OneToOneField'}:
            on_delete = options.pop('on_delete', 'CASCADE')
            args.append(f"on_delete=models.{on_delete}")

        # Other options
        for key, value in sorted(options.items()):
            args.append(f"{key}={self._format_value(value)}")

        return ', '.join(args)

    def _generate_field_args(
        self,
        field_type: str,
        options: Dict[str, Any]
    ) -> str:
        """Generate arguments for regular fields"""
        args = []

        # Order options: positional arguments first, then keyword arguments
        positional_args = []
        keyword_args = {}

        for key, value in options.items():
            # Some arguments are positional in certain field types
            if key == 'max_length' and field_type in {'CharField', 'SlugField', 'EmailField'}:
                positional_args.append(self._format_value(value))
            elif key in {'max_digits', 'decimal_places'} and field_type == 'DecimalField':
                keyword_args[key] = self._format_value(value)
            else:
                keyword_args[key] = self._format_value(value)

        # Combine positional and keyword arguments
        args.extend(positional_args)
        args.extend(f"{k}={v}" for k, v in sorted(keyword_args.items()))

        return ', '.join(args)

    def _format_value(self, value: Any) -> str:
        """Format a Python value for code generation"""
        if isinstance(value, bool):
            return 'True' if value else 'False'
        elif isinstance(value, str):
            # Check for special values
            if value == 'uuid.uuid4':
                return 'uuid.uuid4'
            elif value.startswith('models.'):
                return value
            else:
                return f"'{value}'"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return '[' + ', '.join(self._format_value(v) for v in value) + ']'
        elif isinstance(value, dict):
            return '{' + ', '.join(f"'{k}': {self._format_value(v)}" for k, v in value.items()) + '}'
        elif value is None:
            return 'None'
        else:
            return repr(value)

    def _generate_meta(self) -> List[str]:
        """Generate Meta class"""
        lines = ['    class Meta:']

        meta = self.schema['meta']

        # Handle different meta options
        for key, value in sorted(meta.items()):
            if isinstance(value, str):
                lines.append(f"        {key} = '{value}'")
            elif isinstance(value, list):
                formatted_list = ', '.join(f"'{v}'" if isinstance(v, str) else str(v) for v in value)
                lines.append(f"        {key} = [{formatted_list}]")
            elif isinstance(value, bool):
                lines.append(f"        {key} = {value}")
            elif isinstance(value, dict):
                # For unique_together, indexes, etc.
                lines.append(f"        {key} = {value}")
            else:
                lines.append(f"        {key} = {value}")

        return lines

    def _generate_str_method(self) -> List[str]:
        """Generate __str__ method"""
        # Check if custom __str__ is specified
        str_field = self.schema.get('str_field')

        if str_field:
            return [
                '    def __str__(self):',
                f'        return str(self.{str_field})',
            ]

        # Default: use first CharField or just str(pk)
        for field in self.schema['fields']:
            if field['type'] in {'CharField', 'TextField', 'EmailField', 'SlugField'}:
                return [
                    '    def __str__(self):',
                    f'        return self.{field["name"]}',
                ]

        # Fallback
        return [
            '    def __str__(self):',
            f'        return f"{self.schema["model_name"]} {{self.pk}}"',
        ]

    def _generate_methods(self) -> List[str]:
        """Generate custom methods"""
        lines = []

        for method in self.schema.get('methods', []):
            if 'name' not in method or 'body' not in method:
                continue

            # Method signature
            args = method.get('args', 'self')
            lines.append(f"    def {method['name']}({args}):")

            # Docstring
            if 'docstring' in method:
                lines.append(f'        """{method["docstring"]}"""')

            # Body
            body_lines = method['body'].strip().split('\n')
            for line in body_lines:
                lines.append(f"        {line}")

            lines.append('')

        return lines


def load_schema(filepath: str) -> Dict[str, Any]:
    """Load schema from JSON file"""
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {filepath}")

    with open(path, 'r') as f:
        return json.load(f)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python generate_model.py <schema.json>")
        print("\nExample:")
        print("  python generate_model.py article_schema.json")
        print("  python generate_model.py article_schema.json > models.py")
        print("\nSchema format:")
        print(json.dumps({
            "model_name": "Article",
            "app_label": "blog",
            "description": "Blog article model",
            "fields": [
                {
                    "name": "title",
                    "type": "CharField",
                    "options": {"max_length": 200}
                },
                {
                    "name": "author",
                    "type": "ForeignKey",
                    "options": {
                        "to": "auth.User",
                        "on_delete": "CASCADE",
                        "related_name": "articles"
                    }
                }
            ],
            "meta": {
                "ordering": ["-created_at"]
            },
            "str_field": "title"
        }, indent=2))
        sys.exit(1)

    try:
        schema = load_schema(sys.argv[1])
        generator = ModelGenerator(schema)
        model_code = generator.generate()
        print(model_code)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in schema file: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
