#!/usr/bin/env python
"""
Django Admin Performance Analyzer

Analyzes Django admin classes for performance issues and optimization opportunities.

Usage:
    python admin_analyzer.py myapp.admin
    python admin_analyzer.py myapp.admin.ProductAdmin
    python admin_analyzer.py myapp.admin --format json
"""

import sys
import ast
import argparse
import importlib
import json
from typing import List, Dict, Optional, Any
from pathlib import Path


class Issue:
    """Represents a performance or configuration issue"""

    SEVERITY_ERROR = 'error'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO = 'info'
    SEVERITY_SUCCESS = 'success'

    def __init__(self, severity: str, title: str, description: str,
                 suggestion: Optional[str] = None, location: Optional[str] = None):
        self.severity = severity
        self.title = title
        self.description = description
        self.suggestion = suggestion
        self.location = location

    def to_dict(self) -> Dict:
        return {
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'suggestion': self.suggestion,
            'location': self.location,
        }


class AdminAnalyzer:
    """Analyze Django admin classes for issues"""

    def __init__(self, admin_class, model_class):
        self.admin_class = admin_class
        self.model_class = model_class
        self.issues = []

    def analyze(self) -> List[Issue]:
        """Run all analysis checks"""
        self.issues = []

        # Check list_display optimizations
        self._check_list_display()

        # Check queryset optimizations
        self._check_queryset_optimization()

        # Check filter optimizations
        self._check_filters()

        # Check search optimizations
        self._check_search()

        # Check inline optimizations
        self._check_inlines()

        # Check action optimizations
        self._check_actions()

        # Check fieldsets organization
        self._check_fieldsets()

        return self.issues

    def _check_list_display(self):
        """Check list_display configuration"""
        list_display = getattr(self.admin_class, 'list_display', None)
        if not list_display:
            self.issues.append(Issue(
                Issue.SEVERITY_WARNING,
                'No list_display configured',
                'Admin uses default display (__str__ only)',
                'Add list_display with relevant fields for better overview'
            ))
            return

        # Check for callable methods in list_display
        callables = []
        for field in list_display:
            if callable(getattr(self.admin_class, field, None)):
                callables.append(field)

        if callables:
            # Check if get_queryset optimizes for these callables
            has_optimization = self._has_queryset_method()

            for callable_name in callables:
                # Check if callable accesses related objects
                if self._callable_accesses_relations(callable_name):
                    if not has_optimization:
                        self.issues.append(Issue(
                            Issue.SEVERITY_ERROR,
                            f'N+1 Query Detected in list_display',
                            f'Method "{callable_name}" accesses related objects without optimization',
                            f'Add related fields to list_select_related or optimize in get_queryset()',
                            f'list_display method: {callable_name}'
                        ))

        # Check list_select_related
        list_select_related = getattr(self.admin_class, 'list_select_related', None)
        fk_fields = self._get_foreign_key_fields()

        if fk_fields and not list_select_related:
            displayed_fks = [f for f in list_display if f in fk_fields]
            if displayed_fks:
                self.issues.append(Issue(
                    Issue.SEVERITY_WARNING,
                    'Missing list_select_related',
                    f'Foreign keys displayed but not optimized: {", ".join(displayed_fks)}',
                    f'Add: list_select_related = {displayed_fks}'
                ))
        elif list_select_related:
            self.issues.append(Issue(
                Issue.SEVERITY_SUCCESS,
                'Queryset optimized with list_select_related',
                f'Related fields: {", ".join(list_select_related)}',
            ))

    def _check_queryset_optimization(self):
        """Check get_queryset method for optimizations"""
        has_method = self._has_queryset_method()

        if not has_method:
            # Check if model has relations
            fk_fields = self._get_foreign_key_fields()
            m2m_fields = self._get_many_to_many_fields()
            reverse_relations = self._get_reverse_relations()

            if fk_fields or m2m_fields or reverse_relations:
                self.issues.append(Issue(
                    Issue.SEVERITY_INFO,
                    'Consider optimizing queryset',
                    'Model has relations but no get_queryset() optimization',
                    'Override get_queryset() to add select_related/prefetch_related'
                ))
        else:
            self.issues.append(Issue(
                Issue.SEVERITY_SUCCESS,
                'Custom get_queryset() implemented',
                'Queryset customization in place',
            ))

    def _check_filters(self):
        """Check list_filter configuration"""
        list_filter = getattr(self.admin_class, 'list_filter', None)

        if not list_filter:
            # Suggest filters for boolean and FK fields
            boolean_fields = self._get_boolean_fields()
            fk_fields = self._get_foreign_key_fields()

            if boolean_fields or fk_fields:
                suggested = boolean_fields[:2] + fk_fields[:2]
                self.issues.append(Issue(
                    Issue.SEVERITY_INFO,
                    'No filters configured',
                    'Consider adding filters for easier navigation',
                    f'Suggested: list_filter = {suggested}'
                ))
        else:
            # Check for potentially slow filters
            fk_fields = self._get_foreign_key_fields()
            for filter_field in list_filter:
                if isinstance(filter_field, str) and filter_field in fk_fields:
                    # Check if related model has many objects
                    self.issues.append(Issue(
                        Issue.SEVERITY_INFO,
                        f'Filter on ForeignKey: {filter_field}',
                        'May be slow if related model has many objects',
                        'Consider custom SimpleListFilter or RelatedOnlyFieldListFilter'
                    ))

    def _check_search(self):
        """Check search_fields configuration"""
        search_fields = getattr(self.admin_class, 'search_fields', None)

        if not search_fields:
            # Suggest text fields
            text_fields = self._get_text_fields()
            if text_fields:
                self.issues.append(Issue(
                    Issue.SEVERITY_INFO,
                    'No search configured',
                    'Consider adding search for text fields',
                    f'Suggested: search_fields = {text_fields[:3]}'
                ))
        else:
            # Check if search fields are indexed
            for field_name in search_fields:
                # Remove prefix (^, =, @)
                clean_name = field_name.lstrip('^=@')

                # Check if field exists and is indexed
                if self._is_model_field(clean_name):
                    if not self._field_is_indexed(clean_name):
                        self.issues.append(Issue(
                            Issue.SEVERITY_WARNING,
                            f'Search field not indexed: {clean_name}',
                            'Searching on unindexed field may be slow',
                            f'Add db_index=True to model field "{clean_name}"'
                        ))

    def _check_inlines(self):
        """Check inline configuration"""
        inlines = getattr(self.admin_class, 'inlines', None)

        if inlines:
            for inline_class in inlines:
                # Check if inline has many objects
                self.issues.append(Issue(
                    Issue.SEVERITY_INFO,
                    f'Inline configured: {inline_class.__name__}',
                    'Consider limiting displayed items with max_num',
                    'Add max_num and show_change_link for better performance'
                ))

    def _check_actions(self):
        """Check admin actions"""
        actions = getattr(self.admin_class, 'actions', None)

        if actions:
            self.issues.append(Issue(
                Issue.SEVERITY_SUCCESS,
                'Custom actions available',
                f'{len(actions)} action(s) configured',
            ))

    def _check_fieldsets(self):
        """Check fieldsets organization"""
        fieldsets = getattr(self.admin_class, 'fieldsets', None)
        fields = getattr(self.admin_class, 'fields', None)

        if not fieldsets and not fields:
            # Check if model has many fields
            field_count = len(self._get_model_fields())
            if field_count > 10:
                self.issues.append(Issue(
                    Issue.SEVERITY_INFO,
                    'Many fields without organization',
                    f'Model has {field_count} fields but no fieldsets',
                    'Consider using fieldsets to organize form'
                ))

    # Helper methods

    def _has_queryset_method(self) -> bool:
        """Check if admin has custom get_queryset"""
        return hasattr(self.admin_class, 'get_queryset')

    def _callable_accesses_relations(self, method_name: str) -> bool:
        """Check if method accesses related fields (simplified check)"""
        method = getattr(self.admin_class, method_name, None)
        if not method:
            return False

        # Get method source code (simplified)
        try:
            import inspect
            source = inspect.getsource(method)
            # Simple heuristic: look for obj.foreignkey_name pattern
            fk_fields = self._get_foreign_key_fields()
            for fk in fk_fields:
                if f'obj.{fk}.' in source:
                    return True
        except:
            pass

        return False

    def _get_model_fields(self) -> List[str]:
        """Get all model field names"""
        if not self.model_class:
            return []

        try:
            return [f.name for f in self.model_class._meta.get_fields()]
        except:
            return []

    def _get_foreign_key_fields(self) -> List[str]:
        """Get ForeignKey field names"""
        if not self.model_class:
            return []

        try:
            from django.db.models import ForeignKey
            return [
                f.name for f in self.model_class._meta.get_fields()
                if isinstance(f, ForeignKey)
            ]
        except:
            return []

    def _get_many_to_many_fields(self) -> List[str]:
        """Get ManyToMany field names"""
        if not self.model_class:
            return []

        try:
            from django.db.models import ManyToManyField
            return [
                f.name for f in self.model_class._meta.get_fields()
                if isinstance(f, ManyToManyField)
            ]
        except:
            return []

    def _get_reverse_relations(self) -> List[str]:
        """Get reverse relation names"""
        if not self.model_class:
            return []

        try:
            return [
                f.name for f in self.model_class._meta.get_fields()
                if f.auto_created and not f.concrete
            ]
        except:
            return []

    def _get_boolean_fields(self) -> List[str]:
        """Get boolean field names"""
        if not self.model_class:
            return []

        try:
            from django.db.models import BooleanField
            return [
                f.name for f in self.model_class._meta.get_fields()
                if isinstance(f, BooleanField)
            ]
        except:
            return []

    def _get_text_fields(self) -> List[str]:
        """Get text field names"""
        if not self.model_class:
            return []

        try:
            from django.db.models import CharField, TextField
            return [
                f.name for f in self.model_class._meta.get_fields()
                if isinstance(f, (CharField, TextField))
            ][:3]
        except:
            return []

    def _is_model_field(self, field_name: str) -> bool:
        """Check if field exists on model"""
        if not self.model_class:
            return False

        try:
            self.model_class._meta.get_field(field_name)
            return True
        except:
            return False

    def _field_is_indexed(self, field_name: str) -> bool:
        """Check if field has database index"""
        if not self.model_class:
            return False

        try:
            field = self.model_class._meta.get_field(field_name)
            return field.db_index or field.unique or field.primary_key
        except:
            return False


def format_text_output(results: Dict[str, List[Issue]]) -> str:
    """Format analysis results as text"""
    output = []
    output.append("=" * 80)
    output.append("ADMIN PERFORMANCE ANALYSIS")
    output.append("=" * 80)
    output.append("")

    for admin_name, issues in results.items():
        output.append(admin_name)
        output.append("-" * len(admin_name))
        output.append("")

        if not issues:
            output.append("✓ No issues found")
            output.append("")
            continue

        for issue in issues:
            # Icon based on severity
            icon = {
                Issue.SEVERITY_ERROR: '❌',
                Issue.SEVERITY_WARNING: '⚠️',
                Issue.SEVERITY_INFO: 'ℹ️',
                Issue.SEVERITY_SUCCESS: '✓',
            }.get(issue.severity, '•')

            output.append(f"{icon} {issue.title}")
            output.append(f"   {issue.description}")

            if issue.suggestion:
                output.append(f"   Suggestion: {issue.suggestion}")

            if issue.location:
                output.append(f"   Location: {issue.location}")

            output.append("")

        output.append("")

    return "\n".join(output)


def format_json_output(results: Dict[str, List[Issue]]) -> str:
    """Format analysis results as JSON"""
    json_results = {}
    for admin_name, issues in results.items():
        json_results[admin_name] = [issue.to_dict() for issue in issues]

    return json.dumps(json_results, indent=2)


def analyze_admin_module(module_path: str, specific_admin: Optional[str] = None) -> Dict[str, List[Issue]]:
    """Analyze all admin classes in a module"""
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error: Cannot import module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)

    results = {}

    # Find all ModelAdmin classes
    from django.contrib import admin

    for name in dir(module):
        obj = getattr(module, name)

        # Check if it's a ModelAdmin class (not the base class)
        if (isinstance(obj, type) and
                issubclass(obj, admin.ModelAdmin) and
                obj is not admin.ModelAdmin):

            # If specific admin requested, skip others
            if specific_admin and name != specific_admin:
                continue

            # Get the model this admin is for
            model_class = getattr(obj, 'model', None)

            # Analyze
            analyzer = AdminAnalyzer(obj, model_class)
            issues = analyzer.analyze()

            admin_display_name = f"{name} ({model_class.__name__ if model_class else 'Unknown'})"
            results[admin_display_name] = issues

    if not results:
        if specific_admin:
            print(f"Error: Admin class '{specific_admin}' not found", file=sys.stderr)
        else:
            print(f"Error: No ModelAdmin classes found in '{module_path}'", file=sys.stderr)
        sys.exit(1)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Django admin classes for performance issues'
    )
    parser.add_argument(
        'admin_module',
        help='Admin module path (e.g., myapp.admin or myapp.admin.ProductAdmin)'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    # Parse module path
    if '.' in args.admin_module:
        parts = args.admin_module.rsplit('.', 1)
        if len(parts) == 2 and parts[1][0].isupper():
            # Specific admin class (e.g., myapp.admin.ProductAdmin)
            module_path = parts[0]
            specific_admin = parts[1]
        else:
            # Module only (e.g., myapp.admin)
            module_path = args.admin_module
            specific_admin = None
    else:
        module_path = args.admin_module
        specific_admin = None

    # Analyze
    results = analyze_admin_module(module_path, specific_admin)

    # Format and output
    if args.format == 'json':
        print(format_json_output(results))
    else:
        print(format_text_output(results))

    return 0


if __name__ == '__main__':
    # Setup Django if needed
    try:
        import django
        from django.conf import settings

        if not settings.configured:
            # Try to setup Django
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
            try:
                django.setup()
            except:
                pass  # Continue anyway, some checks will work without full Django setup
    except ImportError:
        pass

    sys.exit(main())
