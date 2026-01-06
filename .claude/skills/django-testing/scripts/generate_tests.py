#!/usr/bin/env python3
"""
Django Test Generator

Generates test boilerplate for Django models and views.

Usage:
    # Generate tests for a model
    python generate_tests.py --model myapp/models.py:Article --output tests/test_article.py

    # Generate tests for a view
    python generate_tests.py --view myapp/views.py:ArticleDetailView --output tests/test_views.py

    # Generate tests for an entire app
    python generate_tests.py --app myapp --output tests/

Features:
    - Generates test boilerplate for models with field validation tests
    - Generates view tests with status code checks
    - Includes common assertions
    - Creates proper test class structure
"""

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


class ModelAnalyzer:
    """Analyzes Django model definitions to generate tests."""

    def __init__(self, file_path: str, model_name: str):
        self.file_path = file_path
        self.model_name = model_name
        self.fields = []
        self.methods = []

    def analyze(self) -> Dict[str, Any]:
        """Parse the model file and extract information."""
        try:
            with open(self.file_path, 'r') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == self.model_name:
                    return self._analyze_class(node)

            raise ValueError(f"Model '{self.model_name}' not found in {self.file_path}")

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise Exception(f"Error analyzing model: {e}")

    def _analyze_class(self, class_node: ast.ClassDef) -> Dict[str, Any]:
        """Extract fields and methods from model class."""
        info = {
            'name': self.model_name,
            'fields': [],
            'methods': [],
            'has_str': False,
            'has_get_absolute_url': False,
        }

        for item in class_node.body:
            # Check for field assignments
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_info = self._analyze_field(target.id, item.value)
                        if field_info:
                            info['fields'].append(field_info)

            # Check for methods
            elif isinstance(item, ast.FunctionDef):
                if item.name == '__str__':
                    info['has_str'] = True
                elif item.name == 'get_absolute_url':
                    info['has_get_absolute_url'] = True
                elif not item.name.startswith('_'):
                    info['methods'].append(item.name)

        return info

    def _analyze_field(self, name: str, value: ast.AST) -> Optional[Dict[str, Any]]:
        """Extract field information."""
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Attribute):
                field_type = value.func.attr
            elif isinstance(value.func, ast.Name):
                field_type = value.func.id
            else:
                return None

            # Skip non-field attributes
            if field_type in ['models', 'Meta']:
                return None

            field_info = {
                'name': name,
                'type': field_type,
                'required': True,
                'max_length': None,
            }

            # Check for blank=True or null=True
            for keyword in value.keywords:
                if keyword.arg in ('blank', 'null'):
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value:
                        field_info['required'] = False
                elif keyword.arg == 'max_length':
                    if isinstance(keyword.value, ast.Constant):
                        field_info['max_length'] = keyword.value.value

            return field_info

        return None


class TestGenerator:
    """Generates test code for Django models and views."""

    def generate_model_tests(self, model_info: Dict[str, Any], app_name: str) -> str:
        """Generate test code for a Django model."""
        model_name = model_info['name']

        # Build imports
        imports = [
            "from django.test import TestCase",
            f"from {app_name}.models import {model_name}",
        ]

        # Check if we need User import
        has_foreign_key = any(
            f['type'] == 'ForeignKey' for f in model_info['fields']
        )
        if has_foreign_key:
            imports.append("from django.contrib.auth import get_user_model")
            imports.append("")
            imports.append("User = get_user_model()")

        imports_str = "\n".join(imports)

        # Generate test class
        test_class = f"""

class {model_name}ModelTests(TestCase):
    \"\"\"Tests for {model_name} model.\"\"\"

    @classmethod
    def setUpTestData(cls):
        \"\"\"Create test data once for all test methods.\"\"\"
"""

        # Add setup for foreign keys
        if has_foreign_key:
            test_class += """        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

"""

        # Add model creation
        test_class += f"        cls.{model_name.lower()} = {model_name}.objects.create(\n"

        # Add field values
        for field in model_info['fields']:
            field_name = field['name']
            field_type = field['type']

            if field_type == 'CharField':
                value = f"'Test {field_name.replace('_', ' ').title()}'"
            elif field_type == 'TextField':
                value = "'Test content for the field'"
            elif field_type == 'IntegerField':
                value = "100"
            elif field_type == 'DecimalField':
                value = "99.99"
            elif field_type == 'BooleanField':
                value = "True"
            elif field_type == 'DateField':
                value = "timezone.now().date()"
                if "from django.utils import timezone" not in imports_str:
                    imports.insert(1, "from django.utils import timezone")
            elif field_type == 'DateTimeField':
                value = "timezone.now()"
                if "from django.utils import timezone" not in imports_str:
                    imports.insert(1, "from django.utils import timezone")
            elif field_type == 'ForeignKey':
                value = "cls.user"
            elif field_type == 'EmailField':
                value = "'test@example.com'"
            elif field_type == 'URLField':
                value = "'https://example.com'"
            elif field_type == 'SlugField':
                value = f"'test-{field_name}'"
            else:
                value = f"'test_{field_name}'"

            if not field['required']:
                continue  # Skip optional fields in basic creation

            test_class += f"            {field_name}={value},\n"

        test_class += "        )\n"

        # Generate test methods
        test_methods = []

        # Test object creation
        test_methods.append(f"""
    def test_{model_name.lower()}_creation(self):
        \"\"\"Test that {model_name} objects can be created.\"\"\"
        self.assertIsNotNone(self.{model_name.lower()}.pk)
        self.assertIsInstance(self.{model_name.lower()}, {model_name})
""")

        # Test __str__ method if exists
        if model_info['has_str']:
            test_methods.append(f"""
    def test_{model_name.lower()}_str_representation(self):
        \"\"\"Test string representation of {model_name}.\"\"\"
        str_repr = str(self.{model_name.lower()})
        self.assertIsInstance(str_repr, str)
        self.assertTrue(len(str_repr) > 0)
""")

        # Test get_absolute_url if exists
        if model_info['has_get_absolute_url']:
            test_methods.append(f"""
    def test_{model_name.lower()}_get_absolute_url(self):
        \"\"\"Test get_absolute_url method returns valid URL.\"\"\"
        url = self.{model_name.lower()}.get_absolute_url()
        self.assertTrue(url.startswith('/'))
""")

        # Test required field validation
        required_fields = [f for f in model_info['fields'] if f['required']]
        if required_fields:
            test_methods.append(f"""
    def test_{model_name.lower()}_required_fields(self):
        \"\"\"Test that required fields are validated.\"\"\"
        from django.core.exceptions import ValidationError

        # Test with empty required field
        {model_name.lower()} = {model_name}()
        with self.assertRaises(ValidationError):
            {model_name.lower()}.full_clean()
""")

        # Test CharField max_length validation
        char_fields = [
            f for f in model_info['fields']
            if f['type'] == 'CharField' and f['max_length']
        ]
        if char_fields:
            field = char_fields[0]
            test_methods.append(f"""
    def test_{model_name.lower()}_{field['name']}_max_length(self):
        \"\"\"Test that {field['name']} enforces max_length.\"\"\"
        from django.core.exceptions import ValidationError

        long_string = 'x' * ({field['max_length']} + 1)
        {model_name.lower()} = {model_name}({field['name']}=long_string)

        with self.assertRaises(ValidationError):
            {model_name.lower()}.full_clean()
""")

        # Test custom methods
        for method_name in model_info['methods']:
            test_methods.append(f"""
    def test_{model_name.lower()}_{method_name}(self):
        \"\"\"Test {method_name} method.\"\"\"
        result = self.{model_name.lower()}.{method_name}()
        # TODO: Add assertions for {method_name}
        self.fail("Test not implemented yet")
""")

        # Combine all parts
        return imports_str + test_class + "".join(test_methods)


    def generate_view_tests(self, view_name: str, app_name: str, view_type: str = 'cbv') -> str:
        """Generate test code for a Django view."""
        imports = [
            "from django.test import TestCase, Client",
            "from django.urls import reverse",
            "from django.contrib.auth import get_user_model",
            "",
            "User = get_user_model()",
        ]

        imports_str = "\n".join(imports)

        test_class = f"""

class {view_name}Tests(TestCase):
    \"\"\"Tests for {view_name} view.\"\"\"

    def setUp(self):
        \"\"\"Set up test client and user.\"\"\"
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_view_url_exists(self):
        \"\"\"Test that view URL exists.\"\"\"
        # TODO: Update with actual URL name
        # url = reverse('view-name')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, 200)
        self.fail("Update URL name and implement test")

    def test_view_uses_correct_template(self):
        \"\"\"Test that view uses correct template.\"\"\"
        # TODO: Update with actual URL and template name
        # url = reverse('view-name')
        # response = self.client.get(url)
        # self.assertTemplateUsed(response, 'app/template.html')
        self.fail("Update template name and implement test")

    def test_view_requires_login(self):
        \"\"\"Test that view requires authentication.\"\"\"
        # TODO: Update with actual URL name
        # url = reverse('view-name')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, 302)  # Redirect to login
        # self.assertIn('/login/', response.url)
        self.fail("Implement authentication test if needed")

    def test_view_with_authenticated_user(self):
        \"\"\"Test view with authenticated user.\"\"\"
        self.client.force_login(self.user)

        # TODO: Update with actual URL name
        # url = reverse('view-name')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, 200)
        self.fail("Implement authenticated test")

    def test_view_context_data(self):
        \"\"\"Test that view provides correct context data.\"\"\"
        self.client.force_login(self.user)

        # TODO: Update with actual URL and context variables
        # url = reverse('view-name')
        # response = self.client.get(url)
        # self.assertIn('key', response.context)
        self.fail("Implement context data test")

    def test_post_request(self):
        \"\"\"Test POST request to view.\"\"\"
        self.client.force_login(self.user)

        # TODO: Update with actual URL and form data
        # url = reverse('view-name')
        # data = {{'field': 'value'}}
        # response = self.client.post(url, data)
        # self.assertEqual(response.status_code, 302)  # Redirect after success
        self.fail("Implement POST test if applicable")
"""

        return imports_str + test_class


def main():
    """Main entry point for the test generator."""
    parser = argparse.ArgumentParser(
        description='Generate Django test boilerplate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate model tests
  python generate_tests.py --model myapp/models.py:Article --output tests/test_article.py

  # Generate view tests
  python generate_tests.py --view myapp/views.py:ArticleDetailView --output tests/test_views.py
        """
    )

    parser.add_argument(
        '--model',
        help='Model to generate tests for (format: path/to/models.py:ModelName)'
    )
    parser.add_argument(
        '--view',
        help='View to generate tests for (format: path/to/views.py:ViewName)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output file path for generated tests'
    )

    args = parser.parse_args()

    # Validate input
    if not args.model and not args.view:
        parser.error("Either --model or --view must be specified")

    if args.model and args.view:
        parser.error("Only one of --model or --view can be specified")

    try:
        generator = TestGenerator()

        if args.model:
            # Parse model specification
            if ':' not in args.model:
                print("Error: Model must be in format 'path/to/models.py:ModelName'")
                sys.exit(1)

            file_path, model_name = args.model.split(':')

            # Extract app name from path
            path_parts = Path(file_path).parts
            if 'models.py' in file_path:
                app_name = path_parts[-2] if len(path_parts) > 1 else 'myapp'
            else:
                app_name = path_parts[0] if path_parts else 'myapp'

            # Analyze model
            print(f"Analyzing model {model_name} in {file_path}...")
            analyzer = ModelAnalyzer(file_path, model_name)
            model_info = analyzer.analyze()

            # Generate tests
            print(f"Generating tests for {model_name}...")
            test_code = generator.generate_model_tests(model_info, app_name)

        elif args.view:
            # Parse view specification
            if ':' not in args.view:
                print("Error: View must be in format 'path/to/views.py:ViewName'")
                sys.exit(1)

            file_path, view_name = args.view.split(':')

            # Extract app name from path
            path_parts = Path(file_path).parts
            if 'views.py' in file_path:
                app_name = path_parts[-2] if len(path_parts) > 1 else 'myapp'
            else:
                app_name = path_parts[0] if path_parts else 'myapp'

            # Generate tests
            print(f"Generating tests for {view_name}...")
            test_code = generator.generate_view_tests(view_name, app_name)

        # Create output directory if needed
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write test file
        with open(output_path, 'w') as f:
            f.write(test_code)

        print(f"\n✓ Test file generated: {output_path}")
        print(f"\nNext steps:")
        print(f"  1. Review and update the generated tests")
        print(f"  2. Replace TODO comments with actual test logic")
        print(f"  3. Run the tests: python manage.py test")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
