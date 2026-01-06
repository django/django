#!/usr/bin/env python
"""
Django Admin Generator

Generates optimized ModelAdmin classes from Django models.

Usage:
    python generate_admin.py path/to/models.py
    python generate_admin.py path/to/models.py --model Product
    python generate_admin.py path/to/models.py -o admin_generated.py
"""

import ast
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Optional


class ModelAnalyzer(ast.NodeVisitor):
    """Analyze Django models to extract field information"""

    def __init__(self):
        self.models = {}
        self.current_model = None
        self.current_class = None

    def visit_ClassDef(self, node):
        """Visit class definitions to find Django models"""
        # Check if class inherits from models.Model
        is_model = any(
            self._is_model_base(base) for base in node.bases
        )

        if is_model:
            self.current_model = node.name
            self.current_class = node
            self.models[node.name] = {
                'name': node.name,
                'fields': [],
                'foreign_keys': [],
                'many_to_many': [],
                'reverse_relations': [],
                'has_str': False,
                'has_get_absolute_url': False,
            }

            # Visit class body
            for item in node.body:
                if isinstance(item, ast.Assign):
                    self._process_field(item)
                elif isinstance(item, ast.FunctionDef):
                    if item.name == '__str__':
                        self.models[node.name]['has_str'] = True
                    elif item.name == 'get_absolute_url':
                        self.models[node.name]['has_get_absolute_url'] = True

        self.generic_visit(node)
        self.current_model = None
        self.current_class = None

    def _is_model_base(self, base):
        """Check if base class is models.Model"""
        if isinstance(base, ast.Attribute):
            return (
                isinstance(base.value, ast.Name) and
                base.value.id == 'models' and
                base.attr == 'Model'
            )
        elif isinstance(base, ast.Name):
            return base.id == 'Model'
        return False

    def _process_field(self, node):
        """Process field assignments"""
        if not self.current_model:
            return

        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue

            field_name = target.id
            if field_name.startswith('_'):
                continue

            # Analyze field type
            field_info = self._analyze_field(field_name, node.value)
            if field_info:
                self.models[self.current_model]['fields'].append(field_info)

                # Track special field types
                if field_info['type'] == 'ForeignKey':
                    self.models[self.current_model]['foreign_keys'].append(field_name)
                elif field_info['type'] == 'ManyToManyField':
                    self.models[self.current_model]['many_to_many'].append(field_name)

    def _analyze_field(self, name, value):
        """Analyze field definition"""
        if not isinstance(value, ast.Call):
            return None

        field_type = self._get_field_type(value.func)
        if not field_type:
            return None

        # Extract field options
        options = {}
        for keyword in value.keywords:
            if keyword.arg in ['max_length', 'blank', 'null', 'choices', 'default']:
                options[keyword.arg] = True

        return {
            'name': name,
            'type': field_type,
            'options': options,
        }

    def _get_field_type(self, node):
        """Get field type name"""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == 'models':
                return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        return None


class AdminGenerator:
    """Generate ModelAdmin code"""

    # Fields suitable for list_display
    DISPLAY_FIELD_TYPES = {
        'CharField', 'TextField', 'IntegerField', 'DecimalField',
        'BooleanField', 'DateField', 'DateTimeField', 'EmailField',
        'URLField', 'SlugField', 'FloatField', 'PositiveIntegerField',
    }

    # Fields suitable for search
    SEARCH_FIELD_TYPES = {
        'CharField', 'TextField', 'EmailField', 'SlugField',
    }

    # Fields suitable for filters
    FILTER_FIELD_TYPES = {
        'BooleanField', 'ForeignKey', 'DateField', 'DateTimeField',
        'IntegerField', 'PositiveIntegerField',
    }

    def __init__(self, models: Dict):
        self.models = models

    def generate(self, model_name: Optional[str] = None) -> str:
        """Generate admin code for models"""
        if model_name:
            if model_name not in self.models:
                raise ValueError(f"Model '{model_name}' not found")
            models_to_generate = [model_name]
        else:
            models_to_generate = list(self.models.keys())

        output = []
        output.append("from django.contrib import admin")
        output.append("from django.utils.html import format_html")
        output.append("from .models import " + ", ".join(models_to_generate))
        output.append("")
        output.append("")

        for name in models_to_generate:
            output.append(self._generate_model_admin(name, self.models[name]))
            output.append("")
            output.append("")

        return "\n".join(output)

    def _generate_model_admin(self, name: str, model_info: Dict) -> str:
        """Generate ModelAdmin class for a model"""
        lines = []
        lines.append(f"@admin.register({name})")
        lines.append(f"class {name}Admin(admin.ModelAdmin):")

        # Determine fields for list_display
        display_fields = self._get_display_fields(model_info)
        if display_fields:
            lines.append(f"    list_display = {display_fields}")

        # Determine search fields
        search_fields = self._get_search_fields(model_info)
        if search_fields:
            lines.append(f"    search_fields = {search_fields}")

        # Determine list_filter
        filter_fields = self._get_filter_fields(model_info)
        if filter_fields:
            lines.append(f"    list_filter = {filter_fields}")

        # Add list_select_related for ForeignKeys
        if model_info['foreign_keys']:
            fk_fields = [f"'{fk}'" for fk in model_info['foreign_keys']]
            lines.append(f"    list_select_related = [{', '.join(fk_fields)}]")

        # Add autocomplete_fields for ForeignKeys
        if model_info['foreign_keys']:
            fk_fields = [f"'{fk}'" for fk in model_info['foreign_keys'][:3]]  # Limit to 3
            lines.append(f"    autocomplete_fields = [{', '.join(fk_fields)}]")

        # Add filter_horizontal for ManyToMany
        if model_info['many_to_many']:
            m2m_fields = [f"'{m2m}'" for m2m in model_info['many_to_many']]
            lines.append(f"    filter_horizontal = [{', '.join(m2m_fields)}]")

        # Add date_hierarchy if date field exists
        date_field = self._get_date_field(model_info)
        if date_field:
            lines.append(f"    date_hierarchy = '{date_field}'")

        # Add ordering
        lines.append(f"    ordering = ['-id']")

        # Add save_on_top for convenience
        lines.append(f"    save_on_top = True")

        # If no options added, add pass
        if len(lines) == 2:
            lines.append("    pass")

        return "\n".join(lines)

    def _get_display_fields(self, model_info: Dict) -> str:
        """Get fields for list_display"""
        fields = ['id']

        for field in model_info['fields']:
            if field['type'] in self.DISPLAY_FIELD_TYPES:
                fields.append(field['name'])
            elif field['type'] == 'ForeignKey':
                # Use related object's __str__
                fields.append(field['name'])

            # Limit to 6 fields for clean display
            if len(fields) >= 6:
                break

        # Format as list
        formatted = [f"'{f}'" for f in fields]
        return "[" + ", ".join(formatted) + "]"

    def _get_search_fields(self, model_info: Dict) -> Optional[str]:
        """Get fields for search_fields"""
        fields = []

        for field in model_info['fields']:
            if field['type'] in self.SEARCH_FIELD_TYPES:
                fields.append(field['name'])

                # Limit to 5 search fields
                if len(fields) >= 5:
                    break

        if not fields:
            return None

        formatted = [f"'{f}'" for f in fields]
        return "[" + ", ".join(formatted) + "]"

    def _get_filter_fields(self, model_info: Dict) -> Optional[str]:
        """Get fields for list_filter"""
        fields = []

        # Add boolean and choice fields first
        for field in model_info['fields']:
            if field['type'] == 'BooleanField':
                fields.append(field['name'])
            elif field['options'].get('choices'):
                fields.append(field['name'])

        # Add ForeignKeys
        for fk in model_info['foreign_keys'][:3]:  # Limit to 3
            fields.append(fk)

        # Add date fields
        for field in model_info['fields']:
            if field['type'] in ['DateField', 'DateTimeField']:
                fields.append(field['name'])
                break  # Only one date filter

        if not fields:
            return None

        # Limit total filters
        fields = fields[:5]
        formatted = [f"'{f}'" for f in fields]
        return "[" + ", ".join(formatted) + "]"

    def _get_date_field(self, model_info: Dict) -> Optional[str]:
        """Get first date field for date_hierarchy"""
        for field in model_info['fields']:
            if field['type'] in ['DateField', 'DateTimeField']:
                return field['name']
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Generate Django admin classes from models'
    )
    parser.add_argument(
        'model_file',
        help='Path to models.py file'
    )
    parser.add_argument(
        '--model',
        help='Generate admin for specific model only'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )

    args = parser.parse_args()

    # Read model file
    model_path = Path(args.model_file)
    if not model_path.exists():
        print(f"Error: File '{args.model_file}' not found", file=sys.stderr)
        return 1

    try:
        with open(model_path, 'r') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    # Parse models
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"Syntax error in model file: {e}", file=sys.stderr)
        return 1

    # Analyze models
    analyzer = ModelAnalyzer()
    analyzer.visit(tree)

    if not analyzer.models:
        print("No Django models found in file", file=sys.stderr)
        return 1

    # Generate admin code
    generator = AdminGenerator(analyzer.models)

    try:
        admin_code = generator.generate(args.model)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Output
    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(admin_code)
            print(f"Generated admin code written to {args.output}")
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            return 1
    else:
        print(admin_code)

    return 0


if __name__ == '__main__':
    sys.exit(main())
