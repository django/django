#!/usr/bin/env python3
"""
Django Code Generator

Base code generator with template rendering, formatting, and import management.
Provides utilities for generating Django code with proper formatting and conventions.

Usage:
    from code_generator import DjangoCodeGenerator

    generator = DjangoCodeGenerator()
    code = generator.render_template('model.py', context={'model_name': 'Article'})
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from textwrap import dedent, indent


@dataclass
class ImportStatement:
    """Represents a Python import statement."""
    module: str
    names: List[str] = field(default_factory=list)
    is_from: bool = True
    alias: Optional[str] = None

    def __str__(self) -> str:
        """Generate import statement string."""
        if self.is_from:
            if self.names:
                names_str = ", ".join(sorted(self.names))
                return f"from {self.module} import {names_str}"
            return f"from {self.module} import *"
        else:
            if self.alias:
                return f"import {self.module} as {self.alias}"
            return f"import {self.module}"

    def __lt__(self, other: 'ImportStatement') -> bool:
        """Enable sorting of import statements."""
        return (self.module, self.is_from) < (other.module, other.is_from)


class ImportManager:
    """Manages Python import statements with Django conventions."""

    # Import order groups following isort/black conventions
    STDLIB_MODULES = {
        "sys", "os", "re", "json", "datetime", "time", "logging",
        "pathlib", "typing", "dataclasses", "abc", "collections",
        "itertools", "functools", "operator", "decimal", "uuid"
    }

    DJANGO_MODULES = {
        "django", "rest_framework"
    }

    def __init__(self):
        """Initialize import manager."""
        self.imports: Dict[str, ImportStatement] = {}

    def add_import(self, module: str, names: Optional[List[str]] = None,
                   is_from: bool = True, alias: Optional[str] = None) -> None:
        """
        Add an import statement.

        Args:
            module: Module to import from
            names: Names to import (for 'from' imports)
            is_from: Whether this is a 'from' import
            alias: Alias for the import
        """
        key = f"{module}::{','.join(sorted(names or []))}"

        if key in self.imports:
            # Merge names if import already exists
            if names and self.imports[key].names:
                self.imports[key].names = sorted(set(self.imports[key].names + names))
        else:
            self.imports[key] = ImportStatement(
                module=module,
                names=names or [],
                is_from=is_from,
                alias=alias
            )

    def add_django_import(self, submodule: str, names: List[str]) -> None:
        """
        Add a Django import.

        Args:
            submodule: Django submodule (e.g., 'db.models', 'forms')
            names: Names to import
        """
        self.add_import(f"django.{submodule}", names)

    def generate_imports(self) -> str:
        """
        Generate formatted import statements following PEP 8 and Django conventions.

        Returns:
            Formatted import statements string
        """
        if not self.imports:
            return ""

        # Group imports
        stdlib_imports = []
        django_imports = []
        third_party_imports = []
        local_imports = []

        for imp in self.imports.values():
            root_module = imp.module.split(".")[0]

            if root_module in self.STDLIB_MODULES:
                stdlib_imports.append(imp)
            elif root_module in self.DJANGO_MODULES:
                django_imports.append(imp)
            elif root_module.startswith(".") or imp.module.startswith("apps."):
                local_imports.append(imp)
            else:
                third_party_imports.append(imp)

        # Sort within each group
        stdlib_imports.sort()
        django_imports.sort()
        third_party_imports.sort()
        local_imports.sort()

        # Build import string
        import_sections = []

        for group in [stdlib_imports, django_imports, third_party_imports, local_imports]:
            if group:
                import_sections.append("\n".join(str(imp) for imp in group))

        return "\n\n".join(import_sections)


class DjangoCodeFormatter:
    """Formats Django code according to PEP 8 and Django style guide."""

    @staticmethod
    def format_model_field(field_name: str, field_type: str,
                          **kwargs: Any) -> str:
        """
        Format a model field definition.

        Args:
            field_name: Name of the field
            field_type: Type of the field (CharField, IntegerField, etc.)
            **kwargs: Field options

        Returns:
            Formatted field definition
        """
        args = []
        field_kwargs = []

        # Handle positional arguments
        if field_type in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
            if "to" in kwargs:
                args.append(f"'{kwargs.pop('to')}'")
            if "on_delete" in kwargs:
                args.append(f"on_delete={kwargs.pop('on_delete')}")

        # Handle keyword arguments
        for key, value in sorted(kwargs.items()):
            if isinstance(value, str):
                field_kwargs.append(f'{key}="{value}"')
            elif isinstance(value, bool):
                field_kwargs.append(f'{key}={str(value)}')
            elif value is None:
                field_kwargs.append(f'{key}=None')
            else:
                field_kwargs.append(f'{key}={value}')

        all_args = args + field_kwargs
        args_str = ", ".join(all_args)

        return f"{field_name} = models.{field_type}({args_str})"

    @staticmethod
    def format_form_field(field_name: str, field_type: str,
                         **kwargs: Any) -> str:
        """
        Format a form field definition.

        Args:
            field_name: Name of the field
            field_type: Type of the field
            **kwargs: Field options

        Returns:
            Formatted field definition
        """
        field_kwargs = []

        for key, value in sorted(kwargs.items()):
            if isinstance(value, str):
                field_kwargs.append(f'{key}="{value}"')
            elif isinstance(value, bool):
                field_kwargs.append(f'{key}={str(value)}')
            elif value is None:
                field_kwargs.append(f'{key}=None')
            else:
                field_kwargs.append(f'{key}={value}')

        args_str = ", ".join(field_kwargs)
        return f"{field_name} = forms.{field_type}({args_str})"

    @staticmethod
    def format_class_definition(class_name: str, base_classes: List[str],
                               docstring: Optional[str] = None,
                               body: Optional[str] = None) -> str:
        """
        Format a class definition.

        Args:
            class_name: Name of the class
            base_classes: List of base class names
            docstring: Optional class docstring
            body: Optional class body

        Returns:
            Formatted class definition
        """
        bases_str = ", ".join(base_classes) if base_classes else ""
        result = f"class {class_name}({bases_str}):\n"

        if docstring:
            result += f'    """{docstring}"""\n\n'

        if body:
            result += indent(body.rstrip(), "    ") + "\n"
        elif not docstring:
            result += "    pass\n"

        return result

    @staticmethod
    def format_function_definition(func_name: str, params: List[Tuple[str, Optional[str]]],
                                   return_type: Optional[str] = None,
                                   docstring: Optional[str] = None,
                                   body: Optional[str] = None,
                                   is_async: bool = False,
                                   decorators: Optional[List[str]] = None) -> str:
        """
        Format a function definition.

        Args:
            func_name: Name of the function
            params: List of (param_name, type_hint) tuples
            return_type: Return type annotation
            docstring: Function docstring
            body: Function body
            is_async: Whether function is async
            decorators: List of decorator strings

        Returns:
            Formatted function definition
        """
        result = ""

        # Add decorators
        if decorators:
            for decorator in decorators:
                result += f"@{decorator}\n"

        # Build parameter list
        param_strs = []
        for param_name, type_hint in params:
            if type_hint:
                param_strs.append(f"{param_name}: {type_hint}")
            else:
                param_strs.append(param_name)

        params_str = ", ".join(param_strs)

        # Build function signature
        async_str = "async " if is_async else ""
        return_str = f" -> {return_type}" if return_type else ""
        result += f"{async_str}def {func_name}({params_str}){return_str}:\n"

        # Add docstring
        if docstring:
            result += f'    """{docstring}"""\n'

        # Add body
        if body:
            result += indent(body.rstrip(), "    ") + "\n"
        elif not docstring:
            result += "    pass\n"

        return result

    @staticmethod
    def format_docstring(summary: str, args: Optional[Dict[str, str]] = None,
                        returns: Optional[str] = None,
                        raises: Optional[Dict[str, str]] = None) -> str:
        """
        Format a docstring in Django style (similar to Google/numpy style).

        Args:
            summary: Summary description
            args: Dictionary of argument names to descriptions
            returns: Return value description
            raises: Dictionary of exception types to descriptions

        Returns:
            Formatted docstring
        """
        lines = [summary, ""]

        if args:
            lines.append("Args:")
            for arg_name, arg_desc in args.items():
                lines.append(f"    {arg_name}: {arg_desc}")
            lines.append("")

        if returns:
            lines.append("Returns:")
            lines.append(f"    {returns}")
            lines.append("")

        if raises:
            lines.append("Raises:")
            for exc_type, exc_desc in raises.items():
                lines.append(f"    {exc_type}: {exc_desc}")
            lines.append("")

        # Remove trailing empty line
        while lines and not lines[-1]:
            lines.pop()

        return "\n".join(lines)


class DjangoCodeGenerator:
    """
    Base code generator for Django applications.
    Provides template rendering and code generation utilities.
    """

    def __init__(self):
        """Initialize the code generator."""
        self.import_manager = ImportManager()
        self.formatter = DjangoCodeFormatter()

    def reset(self) -> None:
        """Reset the generator state."""
        self.import_manager = ImportManager()

    def generate_model(self, model_name: str, fields: List[Dict[str, Any]],
                      meta_options: Optional[Dict[str, Any]] = None,
                      docstring: Optional[str] = None) -> str:
        """
        Generate a Django model class.

        Args:
            model_name: Name of the model
            fields: List of field definitions (dicts with 'name', 'type', and options)
            meta_options: Options for the Meta class
            docstring: Model docstring

        Returns:
            Generated model code
        """
        self.reset()
        self.import_manager.add_django_import("db", ["models"])

        # Build fields
        field_lines = []
        for field_def in fields:
            field_name = field_def.pop("name")
            field_type = field_def.pop("type")

            # Add imports for special field types
            if field_type in ["ForeignKey", "OneToOneField"]:
                field_def.setdefault("on_delete", "models.CASCADE")
            if field_type == "JSONField":
                self.import_manager.add_import("json", None, is_from=False)

            field_line = self.formatter.format_model_field(field_name, field_type, **field_def)
            field_lines.append(field_line)

        body = "\n".join(field_lines)

        # Add Meta class if options provided
        if meta_options:
            meta_lines = []
            for key, value in sorted(meta_options.items()):
                if isinstance(value, str):
                    meta_lines.append(f'{key} = "{value}"')
                elif isinstance(value, (list, tuple)):
                    meta_lines.append(f"{key} = {value}")
                else:
                    meta_lines.append(f"{key} = {value}")

            meta_body = "\n".join(meta_lines)
            meta_class = self.formatter.format_class_definition("Meta", [], body=meta_body)
            body += "\n\n" + meta_class

        # Generate model class
        model_class = self.formatter.format_class_definition(
            model_name,
            ["models.Model"],
            docstring=docstring,
            body=body
        )

        # Combine imports and class
        imports = self.import_manager.generate_imports()
        return f"{imports}\n\n\n{model_class}"

    def generate_form(self, form_name: str, fields: Optional[List[Dict[str, Any]]] = None,
                     model_name: Optional[str] = None,
                     meta_options: Optional[Dict[str, Any]] = None,
                     docstring: Optional[str] = None) -> str:
        """
        Generate a Django form or ModelForm.

        Args:
            form_name: Name of the form
            fields: List of field definitions (for regular forms)
            model_name: Model name (for ModelForm)
            meta_options: Options for the Meta class
            docstring: Form docstring

        Returns:
            Generated form code
        """
        self.reset()
        self.import_manager.add_django_import("", ["forms"])

        is_model_form = model_name is not None
        base_class = "forms.ModelForm" if is_model_form else "forms.Form"

        body_parts = []

        # Add fields for regular forms
        if fields and not is_model_form:
            field_lines = []
            for field_def in fields:
                field_name = field_def.pop("name")
                field_type = field_def.pop("type")
                field_line = self.formatter.format_form_field(field_name, field_type, **field_def)
                field_lines.append(field_line)
            body_parts.append("\n".join(field_lines))

        # Add Meta class for ModelForm
        if is_model_form:
            self.import_manager.add_import(f".models", [model_name])

            meta_lines = [f"model = {model_name}"]

            if meta_options:
                for key, value in sorted(meta_options.items()):
                    if isinstance(value, str):
                        meta_lines.append(f'{key} = "{value}"')
                    elif isinstance(value, list):
                        meta_lines.append(f"{key} = {value}")
                    else:
                        meta_lines.append(f"{key} = {value}")

            meta_body = "\n".join(meta_lines)
            meta_class = self.formatter.format_class_definition("Meta", [], body=meta_body)
            body_parts.append(meta_class)

        body = "\n\n".join(body_parts) if body_parts else None

        # Generate form class
        form_class = self.formatter.format_class_definition(
            form_name,
            [base_class],
            docstring=docstring,
            body=body
        )

        # Combine imports and class
        imports = self.import_manager.generate_imports()
        return f"{imports}\n\n\n{form_class}"

    def generate_view(self, view_name: str, view_type: str = "function",
                     base_classes: Optional[List[str]] = None,
                     decorators: Optional[List[str]] = None,
                     is_async: bool = False,
                     docstring: Optional[str] = None) -> str:
        """
        Generate a Django view.

        Args:
            view_name: Name of the view
            view_type: Type of view ('function' or 'class')
            base_classes: Base classes for CBV
            decorators: List of decorators
            is_async: Whether view is async
            docstring: View docstring

        Returns:
            Generated view code
        """
        self.reset()

        if view_type == "function":
            self.import_manager.add_django_import("http", ["HttpResponse"])
            self.import_manager.add_django_import("shortcuts", ["render"])

            body = 'return render(request, "template.html", {})'

            view_code = self.formatter.format_function_definition(
                view_name,
                [("request", "HttpRequest")],
                return_type="HttpResponse",
                docstring=docstring,
                body=body,
                is_async=is_async,
                decorators=decorators
            )
        else:
            # Class-based view
            self.import_manager.add_django_import("views.generic", base_classes or ["View"])

            base_classes = base_classes or ["View"]
            body = 'template_name = "template.html"'

            view_code = self.formatter.format_class_definition(
                view_name,
                base_classes,
                docstring=docstring,
                body=body
            )

        imports = self.import_manager.generate_imports()
        return f"{imports}\n\n\n{view_code}"

    def generate_admin(self, admin_name: str, model_name: str,
                      list_display: Optional[List[str]] = None,
                      list_filter: Optional[List[str]] = None,
                      search_fields: Optional[List[str]] = None,
                      other_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a Django ModelAdmin class.

        Args:
            admin_name: Name of the admin class
            model_name: Name of the model
            list_display: Fields to display in list view
            list_filter: Fields to filter by
            search_fields: Fields to search
            other_options: Other admin options

        Returns:
            Generated admin code
        """
        self.reset()
        self.import_manager.add_django_import("contrib", ["admin"])
        self.import_manager.add_import(".models", [model_name])

        # Build admin class body
        body_lines = []

        if list_display:
            body_lines.append(f"list_display = {list_display}")

        if list_filter:
            body_lines.append(f"list_filter = {list_filter}")

        if search_fields:
            body_lines.append(f"search_fields = {search_fields}")

        if other_options:
            for key, value in sorted(other_options.items()):
                if isinstance(value, str):
                    body_lines.append(f'{key} = "{value}"')
                else:
                    body_lines.append(f"{key} = {value}")

        body = "\n".join(body_lines) if body_lines else None

        # Generate admin class
        admin_class = self.formatter.format_class_definition(
            admin_name,
            ["admin.ModelAdmin"],
            body=body
        )

        # Add registration
        registration = f"\nadmin.site.register({model_name}, {admin_name})"

        imports = self.import_manager.generate_imports()
        return f"{imports}\n\n\n{admin_class}{registration}\n"

    def generate_test_case(self, test_name: str, test_methods: List[Dict[str, str]],
                          test_class: str = "TestCase",
                          setup_code: Optional[str] = None) -> str:
        """
        Generate a Django test case.

        Args:
            test_name: Name of the test case class
            test_methods: List of test method definitions
            test_class: Base test class to use
            setup_code: Optional setUp method code

        Returns:
            Generated test code
        """
        self.reset()
        self.import_manager.add_django_import("test", [test_class])

        body_parts = []

        # Add setUp if provided
        if setup_code:
            setup_method = self.formatter.format_function_definition(
                "setUp",
                [("self", None)],
                body=setup_code
            )
            body_parts.append(setup_method)

        # Add test methods
        for method_def in test_methods:
            method_name = method_def.get("name", "test_example")
            method_body = method_def.get("body", 'self.assertTrue(True)')
            method_docstring = method_def.get("docstring")

            test_method = self.formatter.format_function_definition(
                method_name,
                [("self", None)],
                docstring=method_docstring,
                body=method_body
            )
            body_parts.append(test_method)

        body = "\n\n".join(body_parts)

        # Generate test class
        test_class_code = self.formatter.format_class_definition(
            test_name,
            [test_class],
            body=body
        )

        imports = self.import_manager.generate_imports()
        return f"{imports}\n\n\n{test_class_code}"


def main():
    """CLI demonstration."""
    generator = DjangoCodeGenerator()

    # Example: Generate a model
    model_code = generator.generate_model(
        "Article",
        fields=[
            {"name": "title", "type": "CharField", "max_length": 200},
            {"name": "content", "type": "TextField"},
            {"name": "created_at", "type": "DateTimeField", "auto_now_add": True},
        ],
        meta_options={"ordering": ["-created_at"]},
        docstring="Article model for blog posts."
    )
    print("Generated Model:")
    print(model_code)
    print("\n" + "="*60 + "\n")

    # Example: Generate a form
    form_code = generator.generate_form(
        "ArticleForm",
        model_name="Article",
        meta_options={"fields": ["title", "content"]},
        docstring="Form for creating and editing articles."
    )
    print("Generated Form:")
    print(form_code)


if __name__ == "__main__":
    main()
