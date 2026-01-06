#!/usr/bin/env python3
"""
Django Project Analyzer

Analyzes Django project structure and extracts metadata including:
- Installed apps
- Models, views, forms detection
- Database configuration
- Async pattern detection
- URL configuration
- Middleware setup

Usage:
    python django_analyzer.py /path/to/project
    python django_analyzer.py /path/to/project --output json
    python django_analyzer.py /path/to/project --check async
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict, field


@dataclass
class ModelInfo:
    """Information about a Django model."""
    name: str
    app: str
    file_path: str
    fields: List[Dict[str, str]] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    meta_options: Dict[str, Any] = field(default_factory=dict)
    is_abstract: bool = False
    managers: List[str] = field(default_factory=list)


@dataclass
class ViewInfo:
    """Information about a Django view."""
    name: str
    app: str
    file_path: str
    view_type: str  # 'function', 'class', 'generic'
    is_async: bool = False
    base_classes: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class FormInfo:
    """Information about a Django form."""
    name: str
    app: str
    file_path: str
    form_type: str  # 'Form', 'ModelForm'
    model: Optional[str] = None
    fields: List[str] = field(default_factory=list)


@dataclass
class AppInfo:
    """Information about a Django app."""
    name: str
    path: str
    has_models: bool = False
    has_views: bool = False
    has_forms: bool = False
    has_urls: bool = False
    has_admin: bool = False
    has_tests: bool = False
    has_migrations: bool = False
    has_templates: bool = False
    has_static: bool = False


@dataclass
class ProjectAnalysis:
    """Complete Django project analysis."""
    project_root: str
    settings_module: Optional[str] = None
    django_version: Optional[str] = None
    python_version: str = ""
    installed_apps: List[str] = field(default_factory=list)
    custom_apps: List[AppInfo] = field(default_factory=list)
    middleware: List[str] = field(default_factory=list)
    databases: Dict[str, Dict[str, str]] = field(default_factory=dict)
    models: List[ModelInfo] = field(default_factory=list)
    views: List[ViewInfo] = field(default_factory=list)
    forms: List[FormInfo] = field(default_factory=list)
    has_async_support: bool = False
    async_patterns: Dict[str, int] = field(default_factory=dict)
    url_patterns_count: int = 0
    template_dirs: List[str] = field(default_factory=list)
    static_dirs: List[str] = field(default_factory=list)


class DjangoProjectAnalyzer:
    """Analyzes Django project structure and extracts metadata."""

    def __init__(self, project_root: str):
        """
        Initialize the analyzer.

        Args:
            project_root: Path to Django project root directory
        """
        self.project_root = Path(project_root).resolve()
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        self.analysis = ProjectAnalysis(project_root=str(self.project_root))
        self.settings_content: Optional[str] = None
        self.settings_ast: Optional[ast.Module] = None

    def analyze(self) -> ProjectAnalysis:
        """
        Run complete project analysis.

        Returns:
            ProjectAnalysis object with all detected metadata
        """
        # Get Python version
        self.analysis.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Find and parse settings
        self._find_settings()

        if self.settings_content:
            self._parse_settings()
            self._detect_databases()
            self._detect_middleware()
            self._detect_template_static_config()

        # Analyze apps
        self._detect_apps()

        # Analyze models, views, forms
        self._analyze_models()
        self._analyze_views()
        self._analyze_forms()

        # Detect async patterns
        self._detect_async_patterns()

        # Analyze URL patterns
        self._analyze_urls()

        return self.analysis

    def _find_settings(self) -> None:
        """Find Django settings file."""
        # Common settings file locations
        settings_paths = [
            self.project_root / "settings.py",
            self.project_root / "config" / "settings.py",
            self.project_root / "settings" / "base.py",
            self.project_root / "settings" / "settings.py",
        ]

        # Also search for settings.py in subdirectories
        for settings_file in self.project_root.rglob("settings.py"):
            if "site-packages" not in str(settings_file) and "venv" not in str(settings_file):
                settings_paths.insert(0, settings_file)
                break

        for path in settings_paths:
            if path.exists():
                try:
                    self.settings_content = path.read_text(encoding='utf-8')
                    self.settings_ast = ast.parse(self.settings_content)
                    self.analysis.settings_module = str(path.relative_to(self.project_root))
                    break
                except Exception as e:
                    print(f"Warning: Could not parse {path}: {e}", file=sys.stderr)

    def _parse_settings(self) -> None:
        """Parse settings file to extract configuration."""
        if not self.settings_ast:
            return

        for node in ast.walk(self.settings_ast):
            # Extract INSTALLED_APPS
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "INSTALLED_APPS":
                        self.analysis.installed_apps = self._extract_list_values(node.value)

    def _extract_list_values(self, node: ast.AST) -> List[str]:
        """Extract string values from a list AST node."""
        values = []
        if isinstance(node, (ast.List, ast.Tuple)):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.append(elt.value)
        return values

    def _extract_dict_values(self, node: ast.AST) -> Dict[str, Any]:
        """Extract values from a dict AST node."""
        result = {}
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    key_str = key.value
                    if isinstance(value, ast.Constant):
                        result[key_str] = value.value
                    elif isinstance(value, ast.Dict):
                        result[key_str] = self._extract_dict_values(value)
                    elif isinstance(value, (ast.List, ast.Tuple)):
                        result[key_str] = self._extract_list_values(value)
        return result

    def _detect_databases(self) -> None:
        """Detect database configuration."""
        if not self.settings_ast:
            return

        for node in ast.walk(self.settings_ast):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DATABASES":
                        if isinstance(node.value, ast.Dict):
                            self.analysis.databases = self._extract_dict_values(node.value)

    def _detect_middleware(self) -> None:
        """Detect middleware configuration."""
        if not self.settings_ast:
            return

        for node in ast.walk(self.settings_ast):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "MIDDLEWARE":
                        self.analysis.middleware = self._extract_list_values(node.value)

    def _detect_template_static_config(self) -> None:
        """Detect template and static file configuration."""
        if not self.settings_ast:
            return

        for node in ast.walk(self.settings_ast):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "TEMPLATES":
                            # Extract template dirs
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                for elt in node.elts:
                                    if isinstance(elt, ast.Dict):
                                        template_config = self._extract_dict_values(elt)
                                        if "DIRS" in template_config:
                                            self.analysis.template_dirs.extend(template_config["DIRS"])
                        elif target.id == "STATICFILES_DIRS":
                            self.analysis.static_dirs = self._extract_list_values(node.value)

    def _detect_apps(self) -> None:
        """Detect and analyze Django apps."""
        # Get custom apps (not third-party)
        custom_app_names = [
            app for app in self.analysis.installed_apps
            if not app.startswith("django.") and "." not in app
        ]

        for app_name in custom_app_names:
            app_path = self.project_root / app_name
            if app_path.exists() and app_path.is_dir():
                app_info = AppInfo(
                    name=app_name,
                    path=str(app_path.relative_to(self.project_root)),
                    has_models=(app_path / "models.py").exists() or (app_path / "models").exists(),
                    has_views=(app_path / "views.py").exists() or (app_path / "views").exists(),
                    has_forms=(app_path / "forms.py").exists(),
                    has_urls=(app_path / "urls.py").exists(),
                    has_admin=(app_path / "admin.py").exists(),
                    has_tests=(app_path / "tests.py").exists() or (app_path / "tests").exists(),
                    has_migrations=(app_path / "migrations").exists(),
                    has_templates=(app_path / "templates").exists(),
                    has_static=(app_path / "static").exists(),
                )
                self.analysis.custom_apps.append(app_info)

    def _analyze_models(self) -> None:
        """Analyze models in the project."""
        for app_info in self.analysis.custom_apps:
            app_path = Path(app_info.path)

            # Check for models.py
            models_file = self.project_root / app_path / "models.py"
            if models_file.exists():
                self._parse_models_file(models_file, app_info.name)

            # Check for models/ directory
            models_dir = self.project_root / app_path / "models"
            if models_dir.exists():
                for model_file in models_dir.glob("*.py"):
                    if model_file.name != "__init__.py":
                        self._parse_models_file(model_file, app_info.name)

    def _parse_models_file(self, file_path: Path, app_name: str) -> None:
        """Parse a models file and extract model information."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Django model
                    base_names = [self._get_name(base) for base in node.bases]
                    if any("Model" in name for name in base_names):
                        model_info = self._extract_model_info(node, app_name, str(file_path))
                        self.analysis.models.append(model_info)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    def _extract_model_info(self, node: ast.ClassDef, app_name: str, file_path: str) -> ModelInfo:
        """Extract detailed information from a model class."""
        model_info = ModelInfo(
            name=node.name,
            app=app_name,
            file_path=file_path
        )

        for item in node.body:
            # Extract fields
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id
                        field_type = self._get_field_type(item.value)

                        # Classify as field or relationship
                        if field_type in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                            model_info.relationships.append({
                                "name": field_name,
                                "type": field_type
                            })
                        elif field_type:
                            model_info.fields.append({
                                "name": field_name,
                                "type": field_type
                            })

            # Extract Meta options
            elif isinstance(item, ast.ClassDef) and item.name == "Meta":
                for meta_item in item.body:
                    if isinstance(meta_item, ast.Assign):
                        for target in meta_item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == "abstract" and isinstance(meta_item.value, ast.Constant):
                                    model_info.is_abstract = bool(meta_item.value.value)
                                # Could extract more Meta options here

        return model_info

    def _get_field_type(self, node: ast.AST) -> Optional[str]:
        """Extract field type from assignment value."""
        if isinstance(node, ast.Call):
            func_name = self._get_name(node.func)
            return func_name
        return None

    def _get_name(self, node: ast.AST) -> str:
        """Get the full name of a node (handles attributes like models.CharField)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _analyze_views(self) -> None:
        """Analyze views in the project."""
        for app_info in self.analysis.custom_apps:
            app_path = Path(app_info.path)

            # Check for views.py
            views_file = self.project_root / app_path / "views.py"
            if views_file.exists():
                self._parse_views_file(views_file, app_info.name)

            # Check for views/ directory
            views_dir = self.project_root / app_path / "views"
            if views_dir.exists():
                for view_file in views_dir.glob("*.py"):
                    if view_file.name != "__init__.py":
                        self._parse_views_file(view_file, app_info.name)

    def _parse_views_file(self, file_path: Path, app_name: str) -> None:
        """Parse a views file and extract view information."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Function-based views
                if isinstance(node, ast.FunctionDef):
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    decorators = [self._get_name(dec) for dec in node.decorator_list]

                    view_info = ViewInfo(
                        name=node.name,
                        app=app_name,
                        file_path=str(file_path),
                        view_type="function",
                        is_async=is_async,
                        decorators=decorators
                    )
                    self.analysis.views.append(view_info)

                # Class-based views
                elif isinstance(node, ast.ClassDef):
                    base_names = [self._get_name(base) for base in node.bases]
                    if any("View" in name for name in base_names):
                        view_type = "generic" if any("generic" in name.lower() for name in base_names) else "class"

                        view_info = ViewInfo(
                            name=node.name,
                            app=app_name,
                            file_path=str(file_path),
                            view_type=view_type,
                            base_classes=base_names
                        )
                        self.analysis.views.append(view_info)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    def _analyze_forms(self) -> None:
        """Analyze forms in the project."""
        for app_info in self.analysis.custom_apps:
            app_path = Path(app_info.path)
            forms_file = self.project_root / app_path / "forms.py"

            if forms_file.exists():
                self._parse_forms_file(forms_file, app_info.name)

    def _parse_forms_file(self, file_path: Path, app_name: str) -> None:
        """Parse a forms file and extract form information."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_names = [self._get_name(base) for base in node.bases]

                    # Check if it's a Form or ModelForm
                    form_type = None
                    if any("ModelForm" in name for name in base_names):
                        form_type = "ModelForm"
                    elif any("Form" in name for name in base_names):
                        form_type = "Form"

                    if form_type:
                        form_info = FormInfo(
                            name=node.name,
                            app=app_name,
                            file_path=str(file_path),
                            form_type=form_type
                        )

                        # Extract Meta.model for ModelForm
                        if form_type == "ModelForm":
                            for item in node.body:
                                if isinstance(item, ast.ClassDef) and item.name == "Meta":
                                    for meta_item in item.body:
                                        if isinstance(meta_item, ast.Assign):
                                            for target in meta_item.targets:
                                                if isinstance(target, ast.Name) and target.id == "model":
                                                    form_info.model = self._get_name(meta_item.value)

                        self.analysis.forms.append(form_info)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    def _detect_async_patterns(self) -> None:
        """Detect async/await patterns in the project."""
        async_counts = {
            "async_views": 0,
            "async_functions": 0,
            "await_statements": 0,
            "async_orm_calls": 0
        }

        # Count async views
        async_counts["async_views"] = sum(1 for view in self.analysis.views if view.is_async)

        # Search for async/await patterns in Python files
        for py_file in self.project_root.rglob("*.py"):
            if "site-packages" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding='utf-8')

                # Count async functions
                async_counts["async_functions"] += content.count("async def ")

                # Count await statements
                async_counts["await_statements"] += content.count("await ")

                # Count async ORM patterns
                if "objects.aget" in content or "objects.acreate" in content or "asave()" in content:
                    async_counts["async_orm_calls"] += 1
            except Exception:
                pass

        self.analysis.async_patterns = async_counts
        self.analysis.has_async_support = any(count > 0 for count in async_counts.values())

    def _analyze_urls(self) -> None:
        """Analyze URL patterns in the project."""
        url_count = 0

        # Find all urls.py files
        for urls_file in self.project_root.rglob("urls.py"):
            if "site-packages" in str(urls_file) or "venv" in str(urls_file):
                continue

            try:
                content = urls_file.read_text(encoding='utf-8')
                # Count path() and re_path() calls
                url_count += content.count("path(")
                url_count += content.count("re_path(")
            except Exception:
                pass

        self.analysis.url_patterns_count = url_count

    def to_json(self, indent: int = 2) -> str:
        """
        Convert analysis to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps(asdict(self.analysis), indent=indent, default=str)

    def to_dict(self) -> Dict:
        """
        Convert analysis to dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self.analysis)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze Django project structure and extract metadata"
    )
    parser.add_argument(
        "project_root",
        help="Path to Django project root directory"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--check",
        choices=["async", "apps", "models", "views"],
        help="Check specific aspect of the project"
    )

    args = parser.parse_args()

    try:
        analyzer = DjangoProjectAnalyzer(args.project_root)
        analysis = analyzer.analyze()

        if args.output == "json":
            print(analyzer.to_json())
        else:
            # Print summary
            print(f"\n{'='*60}")
            print(f"Django Project Analysis: {analysis.project_root}")
            print(f"{'='*60}\n")

            if analysis.settings_module:
                print(f"Settings: {analysis.settings_module}")
            print(f"Python: {analysis.python_version}")

            print(f"\nInstalled Apps: {len(analysis.installed_apps)}")
            for app in analysis.installed_apps:
                print(f"  - {app}")

            print(f"\nCustom Apps: {len(analysis.custom_apps)}")
            for app in analysis.custom_apps:
                print(f"  - {app.name}")
                print(f"    Models: {app.has_models}, Views: {app.has_views}, "
                      f"Forms: {app.has_forms}, Admin: {app.has_admin}")

            print(f"\nModels: {len(analysis.models)}")
            for model in analysis.models[:5]:  # Show first 5
                print(f"  - {model.app}.{model.name} "
                      f"({len(model.fields)} fields, {len(model.relationships)} relationships)")
            if len(analysis.models) > 5:
                print(f"  ... and {len(analysis.models) - 5} more")

            print(f"\nViews: {len(analysis.views)}")
            view_types = {}
            for view in analysis.views:
                view_types[view.view_type] = view_types.get(view.view_type, 0) + 1
            for vtype, count in view_types.items():
                print(f"  - {vtype}: {count}")

            print(f"\nForms: {len(analysis.forms)}")
            for form in analysis.forms[:5]:  # Show first 5
                model_info = f" (model: {form.model})" if form.model else ""
                print(f"  - {form.app}.{form.name} ({form.form_type}){model_info}")

            if analysis.has_async_support:
                print(f"\nAsync Support: Yes")
                print(f"  - Async views: {analysis.async_patterns.get('async_views', 0)}")
                print(f"  - Async functions: {analysis.async_patterns.get('async_functions', 0)}")
                print(f"  - Await statements: {analysis.async_patterns.get('await_statements', 0)}")
            else:
                print(f"\nAsync Support: No")

            print(f"\nURL Patterns: {analysis.url_patterns_count}")

            if analysis.databases:
                print(f"\nDatabases: {len(analysis.databases)}")
                for db_name, db_config in analysis.databases.items():
                    engine = db_config.get("ENGINE", "Unknown")
                    print(f"  - {db_name}: {engine}")

            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
