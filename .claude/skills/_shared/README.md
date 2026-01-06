# Django Skills Shared Utilities

This directory contains shared utilities used across all Django skills.

## Available Utilities

### 1. Django Analyzer (`django_analyzer.py`)

Analyzes Django project structure and extracts comprehensive metadata.

**Features:**
- Detects installed apps and custom apps
- Finds and analyzes models (fields, relationships, Meta options)
- Identifies views (FBV, CBV, async views)
- Detects forms (Form, ModelForm)
- Analyzes database configuration
- Detects async patterns throughout the codebase
- Counts URL patterns
- Returns structured JSON or human-readable summary

**Usage:**
```bash
# Summary output
python django_analyzer.py /path/to/project

# JSON output
python django_analyzer.py /path/to/project --output json

# Check specific aspects
python django_analyzer.py /path/to/project --check async
```

**Example:**
```bash
python django_analyzer.py /home/user/myproject --output summary
```

### 2. Code Generator (`code_generator.py`)

Template-based code generation with Django conventions and PEP 8 compliance.

**Features:**
- Generate models with fields and relationships
- Generate forms (Form and ModelForm)
- Generate views (FBV and CBV)
- Generate ModelAdmin classes
- Generate test cases
- Automatic import management
- Django-style formatting and docstrings

**Usage:**
```python
from code_generator import DjangoCodeGenerator

generator = DjangoCodeGenerator()

# Generate a model
model_code = generator.generate_model(
    "Article",
    fields=[
        {"name": "title", "type": "CharField", "max_length": 200},
        {"name": "content", "type": "TextField"},
    ],
    meta_options={"ordering": ["-created_at"]},
    docstring="Article model for blog posts."
)
print(model_code)

# Generate a ModelForm
form_code = generator.generate_form(
    "ArticleForm",
    model_name="Article",
    meta_options={"fields": ["title", "content"]}
)
print(form_code)

# Generate a view
view_code = generator.generate_view(
    "article_list",
    view_type="function",
    is_async=False
)
print(view_code)
```

**Example Run:**
```bash
python code_generator.py  # Runs demonstration
```

### 3. Validators (`validators.py`)

Comprehensive validation utilities for Django code.

**Features:**
- **Model Validation**: Field types, required parameters, Meta options, __str__ method
- **Form Validation**: Field types, Meta class requirements, ModelForm specifics
- **URL Pattern Validation**: Pattern syntax, duplicate detection, naming conventions
- **Migration Validation**: Migration structure, dependencies, operations

**Usage:**
```python
from validators import (
    validate_model_definition,
    validate_form_definition,
    validate_url_patterns,
    validate_migration
)

# Validate a model
model_code = """
from django.db import models

class Product(models.Model):
    name = models.CharField()  # Missing max_length
    price = models.DecimalField(max_digits=10, decimal_places=2)
"""

errors = validate_model_definition(model_code)
for error in errors:
    print(error)

# Validate a form
form_code = """
from django import forms

class ProductForm(forms.ModelForm):
    # Missing Meta class
    pass
"""

errors = validate_form_definition(form_code)
for error in errors:
    print(error)

# Validate URL patterns
urls_code = """
from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list),  # Missing name
    path('/about/', views.about),  # Leading slash
]
"""

errors = validate_url_patterns(urls_code)
for error in errors:
    print(error)
```

**Example Run:**
```bash
python validators.py  # Runs demonstration
```

## Integration Examples

### Workflow 1: Analyze Project → Generate Code → Validate

```python
from django_analyzer import DjangoProjectAnalyzer
from code_generator import DjangoCodeGenerator
from validators import validate_model_definition

# 1. Analyze existing project
analyzer = DjangoProjectAnalyzer("/path/to/project")
analysis = analyzer.analyze()

print(f"Found {len(analysis.models)} models")
print(f"Async support: {analysis.has_async_support}")

# 2. Generate new model based on project patterns
generator = DjangoCodeGenerator()
model_code = generator.generate_model(
    "NewModel",
    fields=[
        {"name": "title", "type": "CharField", "max_length": 200},
    ]
)

# 3. Validate generated code
errors = validate_model_definition(model_code)
if errors:
    print("Validation errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Code is valid!")
    print(model_code)
```

### Workflow 2: Validate Existing Code

```python
from pathlib import Path
from validators import validate_model_definition

# Read existing model file
model_file = Path("/path/to/models.py")
model_code = model_file.read_text()

# Validate
errors = validate_model_definition(model_code)

# Report errors by severity
error_count = sum(1 for e in errors if e.severity == "error")
warning_count = sum(1 for e in errors if e.severity == "warning")

print(f"Errors: {error_count}, Warnings: {warning_count}")

for error in errors:
    if error.severity == "error":
        print(error)
```

### Workflow 3: Generate Complete App Structure

```python
from code_generator import DjangoCodeGenerator

generator = DjangoCodeGenerator()

# Generate model
model_code = generator.generate_model(
    "Book",
    fields=[
        {"name": "title", "type": "CharField", "max_length": 200},
        {"name": "author", "type": "ForeignKey", "to": "Author", "on_delete": "models.CASCADE"},
        {"name": "published_date", "type": "DateField"},
    ],
    docstring="Book model."
)

# Generate form for the model
form_code = generator.generate_form(
    "BookForm",
    model_name="Book",
    meta_options={"fields": "__all__"}
)

# Generate admin
admin_code = generator.generate_admin(
    "BookAdmin",
    "Book",
    list_display=["title", "author", "published_date"],
    search_fields=["title", "author__name"]
)

# Generate view
view_code = generator.generate_view(
    "BookListView",
    view_type="class",
    base_classes=["ListView"]
)

# Write files or display
print("=== models.py ===")
print(model_code)
print("\n=== forms.py ===")
print(form_code)
print("\n=== admin.py ===")
print(admin_code)
print("\n=== views.py ===")
print(view_code)
```

## Design Principles

### 1. Zero Dependencies (Core Libraries Only)
All utilities use only Python standard library and built-in `ast` module. No external dependencies required.

### 2. Django 5.0+ Focused
Code generation and validation follows Django 5.0+ conventions and best practices.

### 3. Comprehensive Error Handling
All utilities gracefully handle errors and provide helpful error messages.

### 4. Type Hints & Docstrings
All functions include type hints and comprehensive docstrings following Django/Google style.

### 5. CLI & Library Usage
Utilities work both as CLI tools and as importable Python libraries.

## Testing

Run the included demonstrations:

```bash
# Test analyzer
python django_analyzer.py --help

# Test code generator
python code_generator.py

# Test validators
python validators.py
```

## Development

### Adding New Validation Rules

To add a new validation rule to `validators.py`:

1. Add the check in the appropriate validator class (`ModelValidator`, `FormValidator`, etc.)
2. Use descriptive error codes (e.g., `missing_max_length`)
3. Include line numbers when possible
4. Set appropriate severity (`error`, `warning`, `info`)

Example:
```python
def _validate_my_check(self, node: ast.AST) -> None:
    """Validate something."""
    if condition:
        self.add_error(
            "my_error_code",
            "Description of the error",
            line=node.lineno,
            severity="error"
        )
```

### Adding New Code Generators

To add a new generator to `code_generator.py`:

1. Add method to `DjangoCodeGenerator` class
2. Use `ImportManager` for imports
3. Use `DjangoCodeFormatter` for formatting
4. Follow Django conventions

Example:
```python
def generate_my_component(self, name: str, **options) -> str:
    """Generate my component."""
    self.reset()
    self.import_manager.add_django_import("module", ["Class"])
    
    # Generate code
    code = self.formatter.format_class_definition(...)
    
    imports = self.import_manager.generate_imports()
    return f"{imports}\n\n\n{code}"
```

## Support

For issues or questions about these utilities, refer to:
- Main README: `/home/user/django/.claude/README.md`
- Skills Index: `/home/user/django/.claude/SKILLS_INDEX.md`
- Improvement Plan: `/home/user/django/.claude/SKILLS_IMPROVEMENT_PLAN.md`
