#!/usr/bin/env python
"""
Generate a ModelForm from a Django model with appropriate widgets and validation.

Usage:
    python generate_form.py --model myapp.Product --output myapp/forms.py
    python generate_form.py --model myapp.Product --fields name,price,description
    python generate_form.py --model myapp.Product --exclude created_at,updated_at
"""

import argparse
import os
import sys
import django
from pathlib import Path


def setup_django():
    """Setup Django environment."""
    # Find Django settings
    django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')

    if not django_settings:
        # Try to find manage.py
        current_dir = Path.cwd()
        while current_dir != current_dir.parent:
            manage_py = current_dir / 'manage.py'
            if manage_py.exists():
                sys.path.insert(0, str(current_dir))
                # Try common settings module names
                for settings_name in ['settings', 'config.settings', 'project.settings']:
                    try:
                        os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_name)
                        django.setup()
                        return
                    except:
                        pass
            current_dir = current_dir.parent

        print("Error: Could not find Django project. Set DJANGO_SETTINGS_MODULE environment variable.")
        sys.exit(1)
    else:
        django.setup()


def get_model(model_path):
    """
    Get model class from app.Model string.

    Args:
        model_path: String in format 'app_label.ModelName'

    Returns:
        Model class
    """
    from django.apps import apps

    try:
        app_label, model_name = model_path.rsplit('.', 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError) as e:
        print(f"Error: Could not find model '{model_path}': {e}")
        sys.exit(1)


def get_widget_for_field(field):
    """
    Determine appropriate widget for a model field.

    Args:
        field: Django model field instance

    Returns:
        Tuple of (widget_class_name, widget_attrs)
    """
    from django.db import models

    widget_attrs = {}

    # Text fields
    if isinstance(field, models.CharField):
        if field.max_length and field.max_length <= 50:
            return 'forms.TextInput', {'placeholder': f'Enter {field.name}', 'class': 'form-control'}
        else:
            return 'forms.Textarea', {'rows': 3, 'placeholder': f'Enter {field.name}', 'class': 'form-control'}

    elif isinstance(field, models.TextField):
        return 'forms.Textarea', {'rows': 5, 'class': 'form-control'}

    elif isinstance(field, models.EmailField):
        return 'forms.EmailInput', {'placeholder': 'user@example.com', 'class': 'form-control'}

    elif isinstance(field, models.URLField):
        return 'forms.URLInput', {'placeholder': 'https://example.com', 'class': 'form-control'}

    # Numeric fields
    elif isinstance(field, (models.IntegerField, models.DecimalField, models.FloatField)):
        attrs = {'class': 'form-control'}
        if isinstance(field, models.DecimalField):
            attrs['step'] = '0.01'
        if isinstance(field, models.PositiveIntegerField):
            attrs['min'] = '0'
        return 'forms.NumberInput', attrs

    # Date/Time fields
    elif isinstance(field, models.DateField):
        return 'forms.DateInput', {'type': 'date', 'class': 'form-control'}

    elif isinstance(field, models.TimeField):
        return 'forms.TimeInput', {'type': 'time', 'class': 'form-control'}

    elif isinstance(field, models.DateTimeField):
        return 'forms.DateTimeInput', {'type': 'datetime-local', 'class': 'form-control'}

    # Boolean
    elif isinstance(field, models.BooleanField):
        return 'forms.CheckboxInput', {'class': 'form-check-input'}

    # File fields
    elif isinstance(field, models.ImageField):
        return 'forms.FileInput', {'accept': 'image/*', 'class': 'form-control'}

    elif isinstance(field, models.FileField):
        return 'forms.FileInput', {'class': 'form-control'}

    # Foreign key
    elif isinstance(field, models.ForeignKey):
        return 'forms.Select', {'class': 'form-select'}

    # Many-to-many
    elif isinstance(field, models.ManyToManyField):
        return 'forms.CheckboxSelectMultiple', {}

    # Default
    return None, {}


def generate_validators(field):
    """
    Generate validator code for a field.

    Args:
        field: Django model field instance

    Returns:
        List of validator strings
    """
    from django.db import models

    validators = []

    # Email validation
    if isinstance(field, models.EmailField):
        validators.append("# Email validation is automatic")

    # URL validation
    elif isinstance(field, models.URLField):
        validators.append("# URL validation is automatic")

    # Numeric validation
    elif isinstance(field, (models.IntegerField, models.DecimalField, models.FloatField)):
        if isinstance(field, models.PositiveIntegerField):
            validators.append(
                "validators=[MinValueValidator(0, message='Value must be non-negative')]"
            )

    # File size validation for file fields
    elif isinstance(field, (models.FileField, models.ImageField)):
        validators.append("# Add file size validation")
        validators.append("# validators=[validate_file_size]")

    return validators


def generate_form_code(model, fields=None, exclude=None):
    """
    Generate ModelForm code.

    Args:
        model: Django model class
        fields: List of field names to include (None = all)
        exclude: List of field names to exclude

    Returns:
        String containing form class code
    """
    from django.db import models

    app_label = model._meta.app_label
    model_name = model.__name__
    form_name = f"{model_name}Form"

    # Get fields
    model_fields = model._meta.get_fields()

    # Filter fields
    if fields:
        field_list = [f for f in model_fields if f.name in fields and not f.many_to_many]
    elif exclude:
        field_list = [
            f for f in model_fields
            if f.name not in exclude
            and not f.many_to_many
            and not f.auto_created
            and f.concrete
            and not isinstance(f, models.AutoField)
        ]
    else:
        field_list = [
            f for f in model_fields
            if not f.many_to_many
            and not f.auto_created
            and f.concrete
            and not isinstance(f, models.AutoField)
        ]

    # Generate imports
    imports = [
        "from django import forms",
        f"from .models import {model_name}",
    ]

    # Check if we need validators
    needs_validators = any(
        isinstance(f, (models.PositiveIntegerField, models.FileField, models.ImageField))
        for f in field_list
    )

    if needs_validators:
        imports.append("from django.core.validators import MinValueValidator")
        imports.append("# from django.core.exceptions import ValidationError")

    # Generate form class
    code = []
    code.append("\n".join(imports))
    code.append("\n")
    code.append(f"class {form_name}(forms.ModelForm):")
    code.append('    """')
    code.append(f'    Form for {model_name} model.')
    code.append('    """')
    code.append("")

    # Generate field overrides with validation
    for field in field_list:
        if isinstance(field, (models.FileField, models.ImageField)):
            widget_class, widget_attrs = get_widget_for_field(field)
            validators = generate_validators(field)

            if validators:
                code.append(f"    # {field.name} = forms.FileField(")
                for validator in validators:
                    code.append(f"    #     {validator}")
                code.append("    # )")
                code.append("")

    # Generate Meta class
    code.append("    class Meta:")
    code.append(f"        model = {model_name}")

    if fields:
        field_names = [f.name for f in field_list]
        code.append(f"        fields = {field_names}")
    elif exclude:
        code.append(f"        exclude = {exclude}")
    else:
        code.append("        fields = '__all__'")

    # Generate widgets
    widgets_dict = {}
    labels_dict = {}
    help_texts_dict = {}

    for field in field_list:
        widget_class, widget_attrs = get_widget_for_field(field)

        if widget_class:
            attrs_str = ", ".join(f"'{k}': '{v}'" for k, v in widget_attrs.items())
            widgets_dict[field.name] = f"{widget_class}(attrs={{{attrs_str}}})"

        # Generate label
        label = field.verbose_name if hasattr(field, 'verbose_name') else field.name.replace('_', ' ').title()
        labels_dict[field.name] = label

        # Generate help text
        if field.help_text:
            help_texts_dict[field.name] = str(field.help_text)

    if widgets_dict:
        code.append("        widgets = {")
        for field_name, widget_code in widgets_dict.items():
            code.append(f"            '{field_name}': {widget_code},")
        code.append("        }")

    if labels_dict:
        code.append("        labels = {")
        for field_name, label in labels_dict.items():
            code.append(f"            '{field_name}': '{label}',")
        code.append("        }")

    if help_texts_dict:
        code.append("        help_texts = {")
        for field_name, help_text in help_texts_dict.items():
            code.append(f"            '{field_name}': '{help_text}',")
        code.append("        }")

    # Generate validation methods
    code.append("")
    code.append("    def clean(self):")
    code.append("        \"\"\"Cross-field validation.\"\"\"")
    code.append("        cleaned_data = super().clean()")
    code.append("        # Add your cross-field validation here")
    code.append("        return cleaned_data")

    # Add field-specific validation examples
    for field in field_list:
        if isinstance(field, models.CharField) and not isinstance(field, (models.EmailField, models.URLField)):
            code.append("")
            code.append(f"    def clean_{field.name}(self):")
            code.append(f"        \"\"\"Validate {field.name}.\"\"\"")
            code.append(f"        {field.name} = self.cleaned_data.get('{field.name}')")
            code.append(f"        # Add validation logic here")
            code.append(f"        return {field.name}")
            break  # Only show one example

    return "\n".join(code)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate ModelForm from Django model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model myapp.Product
  %(prog)s --model myapp.Product --output myapp/forms.py
  %(prog)s --model myapp.Product --fields name,price,description
  %(prog)s --model myapp.Product --exclude created_at,updated_at
        """
    )

    parser.add_argument(
        '--model',
        required=True,
        help='Model path in format app_label.ModelName (e.g., myapp.Product)'
    )
    parser.add_argument(
        '--output',
        help='Output file path (default: print to stdout)'
    )
    parser.add_argument(
        '--fields',
        help='Comma-separated list of fields to include'
    )
    parser.add_argument(
        '--exclude',
        help='Comma-separated list of fields to exclude'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.fields and args.exclude:
        print("Error: Cannot specify both --fields and --exclude")
        sys.exit(1)

    # Setup Django
    setup_django()

    # Get model
    model = get_model(args.model)

    # Parse fields
    fields = args.fields.split(',') if args.fields else None
    exclude = args.exclude.split(',') if args.exclude else None

    # Generate form code
    form_code = generate_form_code(model, fields=fields, exclude=exclude)

    # Output
    if args.output:
        output_path = Path(args.output)

        # Check if file exists
        if output_path.exists():
            response = input(f"File {args.output} exists. Append? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                sys.exit(0)
            mode = 'a'
        else:
            # Create directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mode = 'w'

        with open(output_path, mode) as f:
            if mode == 'a':
                f.write("\n\n")
            f.write(form_code)
            f.write("\n")

        print(f"Form generated successfully: {args.output}")
    else:
        print(form_code)


if __name__ == '__main__':
    main()
