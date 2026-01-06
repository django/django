#!/usr/bin/env python3
"""
Django Code Validators

Validation utilities for Django code including:
- Model validation
- Form field validation
- URL pattern validation
- Migration validation
- Django system check integration

Usage:
    from validators import validate_model_definition, validate_form_definition

    errors = validate_model_definition(model_code)
    if errors:
        print("Validation errors:", errors)
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple


@dataclass
class ValidationError:
    """Represents a validation error."""
    code: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # 'error', 'warning', 'info'

    def __str__(self) -> str:
        """Format error message."""
        location = ""
        if self.line is not None:
            location = f" (line {self.line}"
            if self.column is not None:
                location += f", col {self.column}"
            location += ")"

        return f"[{self.severity.upper()}] {self.code}: {self.message}{location}"


class DjangoValidator:
    """Base validator for Django code."""

    def __init__(self):
        """Initialize validator."""
        self.errors: List[ValidationError] = []

    def add_error(self, code: str, message: str, line: Optional[int] = None,
                  column: Optional[int] = None, severity: str = "error") -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(
            code=code,
            message=message,
            line=line,
            column=column,
            severity=severity
        ))

    def clear_errors(self) -> None:
        """Clear all errors."""
        self.errors = []

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(e.severity == "error" for e in self.errors)

    def get_errors(self) -> List[ValidationError]:
        """Get all errors."""
        return self.errors


class ModelValidator(DjangoValidator):
    """Validates Django model definitions."""

    # Valid model field types
    FIELD_TYPES = {
        "AutoField", "BigAutoField", "BigIntegerField", "BinaryField",
        "BooleanField", "CharField", "DateField", "DateTimeField",
        "DecimalField", "DurationField", "EmailField", "FileField",
        "FilePathField", "FloatField", "ImageField", "IntegerField",
        "GenericIPAddressField", "JSONField", "PositiveIntegerField",
        "PositiveBigIntegerField", "PositiveSmallIntegerField",
        "SlugField", "SmallAutoField", "SmallIntegerField", "TextField",
        "TimeField", "URLField", "UUIDField",
        "ForeignKey", "ManyToManyField", "OneToOneField"
    }

    # Fields that require max_length
    MAX_LENGTH_REQUIRED = {"CharField", "SlugField"}

    # Relationship fields
    RELATION_FIELDS = {"ForeignKey", "ManyToManyField", "OneToOneField"}

    # Valid on_delete options
    ON_DELETE_OPTIONS = {"CASCADE", "PROTECT", "SET_NULL", "SET_DEFAULT", "DO_NOTHING"}

    def validate_model_definition(self, code: str) -> List[ValidationError]:
        """
        Validate a Django model definition.

        Args:
            code: Python code containing model definition

        Returns:
            List of validation errors
        """
        self.clear_errors()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.add_error(
                "syntax_error",
                f"Syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset
            )
            return self.errors

        # Find model classes
        model_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [self._get_name(base) for base in node.bases]
                if any("Model" in name for name in base_names):
                    model_classes.append(node)

        if not model_classes:
            self.add_error(
                "no_model_found",
                "No Django model class found in code",
                severity="warning"
            )

        for model_class in model_classes:
            self._validate_model_class(model_class)

        return self.errors

    def _validate_model_class(self, node: ast.ClassDef) -> None:
        """Validate a single model class."""
        has_fields = False
        has_meta = False
        has_str_method = False
        field_names = set()

        for item in node.body:
            # Check for fields
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id

                        # Check for reserved names
                        if field_name in {"pk", "id"} and not field_name == "id":
                            self.add_error(
                                "reserved_field_name",
                                f"Field name '{field_name}' may conflict with Django internals",
                                line=item.lineno,
                                severity="warning"
                            )

                        # Check for duplicate fields
                        if field_name in field_names:
                            self.add_error(
                                "duplicate_field",
                                f"Duplicate field name '{field_name}'",
                                line=item.lineno
                            )
                        field_names.add(field_name)

                        # Validate field definition
                        if isinstance(item.value, ast.Call):
                            self._validate_field(field_name, item.value, item.lineno)
                            has_fields = True

            # Check for Meta class
            elif isinstance(item, ast.ClassDef) and item.name == "Meta":
                has_meta = True
                self._validate_meta_class(item, node.name)

            # Check for __str__ method
            elif isinstance(item, ast.FunctionDef) and item.name == "__str__":
                has_str_method = True

        if not has_fields:
            self.add_error(
                "no_fields",
                f"Model '{node.name}' has no fields defined",
                line=node.lineno,
                severity="warning"
            )

        if not has_str_method:
            self.add_error(
                "no_str_method",
                f"Model '{node.name}' should define a __str__ method",
                line=node.lineno,
                severity="warning"
            )

    def _validate_field(self, field_name: str, call_node: ast.Call, line: int) -> None:
        """Validate a model field definition."""
        field_type = self._get_name(call_node.func)

        # Extract field type name (e.g., 'CharField' from 'models.CharField')
        if "." in field_type:
            field_type = field_type.split(".")[-1]

        # Check if field type is valid
        if field_type not in self.FIELD_TYPES:
            self.add_error(
                "unknown_field_type",
                f"Unknown field type '{field_type}'",
                line=line,
                severity="warning"
            )
            return

        # Get field arguments
        field_kwargs = {}
        for keyword in call_node.keywords:
            if isinstance(keyword.value, ast.Constant):
                field_kwargs[keyword.arg] = keyword.value.value

        # Check max_length requirement
        if field_type in self.MAX_LENGTH_REQUIRED:
            if "max_length" not in field_kwargs:
                self.add_error(
                    "missing_max_length",
                    f"Field '{field_name}' of type {field_type} requires max_length parameter",
                    line=line
                )

        # Check relationship field requirements
        if field_type in self.RELATION_FIELDS:
            # Check for related model (first positional argument or 'to' keyword)
            has_related_model = len(call_node.args) > 0 or any(
                k.arg == "to" for k in call_node.keywords
            )

            if not has_related_model:
                self.add_error(
                    "missing_related_model",
                    f"Relationship field '{field_name}' must specify related model",
                    line=line
                )

            # Check for on_delete (required for ForeignKey and OneToOneField)
            if field_type in {"ForeignKey", "OneToOneField"}:
                has_on_delete = any(k.arg == "on_delete" for k in call_node.keywords)
                if not has_on_delete:
                    self.add_error(
                        "missing_on_delete",
                        f"Field '{field_name}' of type {field_type} requires on_delete parameter",
                        line=line
                    )

        # Check for common mistakes
        if "unique" in field_kwargs and field_kwargs["unique"] and "db_index" in field_kwargs:
            self.add_error(
                "redundant_db_index",
                f"Field '{field_name}' has unique=True, db_index is redundant",
                line=line,
                severity="warning"
            )

        if "blank" in field_kwargs and field_type == "BooleanField":
            self.add_error(
                "boolean_blank",
                f"BooleanField '{field_name}' should not use blank=True, use NullBooleanField instead",
                line=line,
                severity="warning"
            )

    def _validate_meta_class(self, meta_node: ast.ClassDef, model_name: str) -> None:
        """Validate Meta class."""
        meta_options = {}

        for item in meta_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        option_name = target.id
                        meta_options[option_name] = item.value

        # Check for verbose_name_plural with verbose_name
        if "verbose_name" in meta_options and "verbose_name_plural" not in meta_options:
            self.add_error(
                "missing_verbose_name_plural",
                f"Model '{model_name}' Meta defines verbose_name but not verbose_name_plural",
                line=meta_node.lineno,
                severity="info"
            )

    def _get_name(self, node: ast.AST) -> str:
        """Get the full name of a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""


class FormValidator(DjangoValidator):
    """Validates Django form definitions."""

    FIELD_TYPES = {
        "BooleanField", "CharField", "ChoiceField", "DateField",
        "DateTimeField", "DecimalField", "DurationField", "EmailField",
        "FileField", "FloatField", "ImageField", "IntegerField",
        "GenericIPAddressField", "MultipleChoiceField", "SlugField",
        "TimeField", "URLField", "UUIDField", "RegexField",
        "TypedChoiceField", "TypedMultipleChoiceField",
        "ModelChoiceField", "ModelMultipleChoiceField"
    }

    def validate_form_definition(self, code: str) -> List[ValidationError]:
        """
        Validate a Django form definition.

        Args:
            code: Python code containing form definition

        Returns:
            List of validation errors
        """
        self.clear_errors()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.add_error(
                "syntax_error",
                f"Syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset
            )
            return self.errors

        # Find form classes
        form_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [self._get_name(base) for base in node.bases]
                if any("Form" in name for name in base_names):
                    form_classes.append(node)

        if not form_classes:
            self.add_error(
                "no_form_found",
                "No Django form class found in code",
                severity="warning"
            )

        for form_class in form_classes:
            self._validate_form_class(form_class)

        return self.errors

    def _validate_form_class(self, node: ast.ClassDef) -> None:
        """Validate a single form class."""
        base_names = [self._get_name(base) for base in node.bases]
        is_model_form = any("ModelForm" in name for name in base_names)

        has_fields = False
        has_meta = False
        field_names = set()

        for item in node.body:
            # Check for fields
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id

                        if field_name in field_names:
                            self.add_error(
                                "duplicate_field",
                                f"Duplicate field name '{field_name}'",
                                line=item.lineno
                            )
                        field_names.add(field_name)

                        if isinstance(item.value, ast.Call):
                            self._validate_form_field(field_name, item.value, item.lineno)
                            has_fields = True

            # Check for Meta class
            elif isinstance(item, ast.ClassDef) and item.name == "Meta":
                has_meta = True
                self._validate_form_meta(item, node.name, is_model_form)

        if is_model_form and not has_meta:
            self.add_error(
                "modelform_no_meta",
                f"ModelForm '{node.name}' should define a Meta class",
                line=node.lineno
            )

        if not is_model_form and not has_fields:
            self.add_error(
                "form_no_fields",
                f"Form '{node.name}' has no fields defined",
                line=node.lineno,
                severity="warning"
            )

    def _validate_form_field(self, field_name: str, call_node: ast.Call, line: int) -> None:
        """Validate a form field definition."""
        field_type = self._get_name(call_node.func)

        if "." in field_type:
            field_type = field_type.split(".")[-1]

        if field_type not in self.FIELD_TYPES:
            self.add_error(
                "unknown_field_type",
                f"Unknown form field type '{field_type}'",
                line=line,
                severity="warning"
            )

    def _validate_form_meta(self, meta_node: ast.ClassDef, form_name: str,
                           is_model_form: bool) -> None:
        """Validate Meta class in form."""
        has_model = False
        has_fields = False

        for item in meta_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "model":
                            has_model = True
                        elif target.id == "fields":
                            has_fields = True

        if is_model_form and not has_model:
            self.add_error(
                "modelform_no_model",
                f"ModelForm '{form_name}' Meta class must specify model",
                line=meta_node.lineno
            )

        if is_model_form and not has_fields:
            self.add_error(
                "modelform_no_fields",
                f"ModelForm '{form_name}' Meta class should specify fields",
                line=meta_node.lineno,
                severity="warning"
            )

    def _get_name(self, node: ast.AST) -> str:
        """Get the full name of a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""


class URLValidator(DjangoValidator):
    """Validates Django URL patterns."""

    def validate_url_patterns(self, code: str) -> List[ValidationError]:
        """
        Validate Django URL patterns.

        Args:
            code: Python code containing URL patterns

        Returns:
            List of validation errors
        """
        self.clear_errors()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.add_error(
                "syntax_error",
                f"Syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset
            )
            return self.errors

        # Find urlpatterns
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "urlpatterns":
                        self._validate_urlpatterns_list(node.value)

        return self.errors

    def _validate_urlpatterns_list(self, node: ast.AST) -> None:
        """Validate urlpatterns list."""
        if not isinstance(node, (ast.List, ast.Tuple)):
            self.add_error(
                "urlpatterns_not_list",
                "urlpatterns should be a list or tuple",
                line=getattr(node, "lineno", None)
            )
            return

        if not node.elts:
            self.add_error(
                "empty_urlpatterns",
                "urlpatterns is empty",
                line=node.lineno,
                severity="warning"
            )

        path_patterns = set()

        for elt in node.elts:
            if isinstance(elt, ast.Call):
                func_name = self._get_name(elt.func)

                # Check for valid URL function
                if func_name not in ["path", "re_path", "include"]:
                    self.add_error(
                        "invalid_url_function",
                        f"Unknown URL function '{func_name}'",
                        line=elt.lineno,
                        severity="warning"
                    )
                    continue

                # Get the URL pattern (first argument)
                if elt.args:
                    pattern_node = elt.args[0]
                    if isinstance(pattern_node, ast.Constant):
                        pattern = pattern_node.value

                        # Check for duplicate patterns
                        if pattern in path_patterns:
                            self.add_error(
                                "duplicate_url_pattern",
                                f"Duplicate URL pattern '{pattern}'",
                                line=elt.lineno
                            )
                        path_patterns.add(pattern)

                        # Validate pattern format
                        if func_name == "path":
                            self._validate_path_pattern(pattern, elt.lineno)
                        elif func_name == "re_path":
                            self._validate_regex_pattern(pattern, elt.lineno)

                # Check for name parameter
                has_name = any(k.arg == "name" for k in elt.keywords)
                if not has_name and func_name != "include":
                    self.add_error(
                        "url_no_name",
                        "URL pattern should have a name parameter for reverse lookups",
                        line=elt.lineno,
                        severity="info"
                    )

    def _validate_path_pattern(self, pattern: str, line: int) -> None:
        """Validate path() pattern syntax."""
        # Check for regex characters (should use re_path instead)
        regex_chars = r"[]()^$.*+?{}|\\"
        if any(char in pattern for char in regex_chars):
            self.add_error(
                "path_contains_regex",
                f"path() pattern contains regex characters, use re_path() instead",
                line=line,
                severity="warning"
            )

        # Check for leading slash
        if pattern.startswith("/"):
            self.add_error(
                "leading_slash",
                "URL pattern should not start with '/'",
                line=line,
                severity="warning"
            )

    def _validate_regex_pattern(self, pattern: str, line: int) -> None:
        """Validate re_path() pattern syntax."""
        try:
            re.compile(pattern)
        except re.error as e:
            self.add_error(
                "invalid_regex",
                f"Invalid regex pattern: {e}",
                line=line
            )

    def _get_name(self, node: ast.AST) -> str:
        """Get the full name of a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""


class MigrationValidator(DjangoValidator):
    """Validates Django migrations."""

    def validate_migration(self, code: str) -> List[ValidationError]:
        """
        Validate a Django migration file.

        Args:
            code: Python code containing migration

        Returns:
            List of validation errors
        """
        self.clear_errors()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.add_error(
                "syntax_error",
                f"Syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset
            )
            return self.errors

        # Find Migration class
        migration_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Migration":
                migration_class = node
                break

        if not migration_class:
            self.add_error(
                "no_migration_class",
                "No Migration class found",
                severity="error"
            )
            return self.errors

        self._validate_migration_class(migration_class)

        return self.errors

    def _validate_migration_class(self, node: ast.ClassDef) -> None:
        """Validate Migration class."""
        has_dependencies = False
        has_operations = False

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "dependencies":
                            has_dependencies = True
                        elif target.id == "operations":
                            has_operations = True
                            if isinstance(item.value, (ast.List, ast.Tuple)):
                                if not item.value.elts:
                                    self.add_error(
                                        "empty_operations",
                                        "Migration has empty operations list",
                                        line=item.lineno,
                                        severity="warning"
                                    )

        if not has_dependencies:
            self.add_error(
                "no_dependencies",
                "Migration should declare dependencies",
                line=node.lineno,
                severity="warning"
            )

        if not has_operations:
            self.add_error(
                "no_operations",
                "Migration should have operations list",
                line=node.lineno
            )


# Convenience functions

def validate_model_definition(code: str) -> List[ValidationError]:
    """Validate a Django model definition."""
    validator = ModelValidator()
    return validator.validate_model_definition(code)


def validate_form_definition(code: str) -> List[ValidationError]:
    """Validate a Django form definition."""
    validator = FormValidator()
    return validator.validate_form_definition(code)


def validate_url_patterns(code: str) -> List[ValidationError]:
    """Validate Django URL patterns."""
    validator = URLValidator()
    return validator.validate_url_patterns(code)


def validate_migration(code: str) -> List[ValidationError]:
    """Validate a Django migration."""
    validator = MigrationValidator()
    return validator.validate_migration(code)


def main():
    """CLI demonstration."""
    import sys

    # Example model code
    model_code = """
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Article'

    def __str__(self):
        return self.title
"""

    print("Validating Model Code:")
    print("=" * 60)
    errors = validate_model_definition(model_code)

    if errors:
        for error in errors:
            print(error)
    else:
        print("✓ No errors found")

    print("\n" + "=" * 60 + "\n")

    # Example form code with issues
    form_code = """
from django import forms
from .models import Article

class ArticleForm(forms.ModelForm):
    # Missing Meta class
    pass
"""

    print("Validating Form Code:")
    print("=" * 60)
    errors = validate_form_definition(form_code)

    if errors:
        for error in errors:
            print(error)
    else:
        print("✓ No errors found")


if __name__ == "__main__":
    main()
