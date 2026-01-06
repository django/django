#!/usr/bin/env python
"""
Django Cache Analyzer

Analyzes Django applications for caching opportunities and issues.

Usage:
    python cache_analyzer.py analyze [--app APP_NAME] [--verbose]
    python cache_analyzer.py check-invalidation [--app APP_NAME]
    python cache_analyzer.py report [--output FILE]

Features:
    - Detects expensive database queries that could be cached
    - Finds views without caching
    - Identifies cache invalidation issues
    - Reports optimization opportunities
"""

import os
import sys
import ast
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Set


class DjangoCodeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Django code for caching opportunities"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues = []
        self.stats = {
            'queries': 0,
            'cached_queries': 0,
            'views': 0,
            'cached_views': 0,
            'signals': 0,
            'cache_invalidations': 0,
        }
        self.current_function = None
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions"""
        prev_function = self.current_function
        self.current_function = node.name

        # Check if it's a view function
        if self._is_view_function(node):
            self.stats['views'] += 1
            self._check_view_caching(node)

        # Check for expensive operations
        self._check_expensive_queries(node)

        # Check for cache operations
        self._check_cache_operations(node)

        self.generic_visit(node)
        self.current_function = prev_function

    def visit_ClassDef(self, node: ast.ClassDef):
        """Analyze class definitions"""
        prev_class = self.current_class
        self.current_class = node.name

        # Check if it's a CBV
        if self._is_class_based_view(node):
            self.stats['views'] += 1
            self._check_cbv_caching(node)

        # Check if it's a model
        if self._is_model_class(node):
            self._check_model_caching(node)

        self.generic_visit(node)
        self.current_class = prev_class

    def _is_view_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is a Django view"""
        # Has 'request' as first parameter
        if not node.args.args:
            return False

        first_arg = node.args.args[0].arg
        if first_arg not in ['request', 'self']:
            return False

        # Returns HttpResponse-like object
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return):
                return True

        return False

    def _is_class_based_view(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django CBV"""
        # Check base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                if 'View' in base.id or 'APIView' in base.id:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ['View', 'APIView', 'ListView', 'DetailView']:
                    return True
        return False

    def _is_model_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django model"""
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == 'Model':
                    return True
        return False

    def _check_view_caching(self, node: ast.FunctionDef):
        """Check if view uses caching"""
        has_cache_decorator = self._has_cache_decorator(node)
        has_cache_operations = self._contains_cache_operations(node)

        if not has_cache_decorator and not has_cache_operations:
            self.issues.append({
                'type': 'missing_cache',
                'severity': 'info',
                'location': f'{self.filepath}:{node.lineno}',
                'message': f'View function "{node.name}" could benefit from caching',
                'suggestion': f'Consider adding @cache_page decorator or manual caching'
            })
        else:
            self.stats['cached_views'] += 1

    def _check_cbv_caching(self, node: ast.ClassDef):
        """Check if class-based view uses caching"""
        # Check for cache_page in dispatch method decorator
        for decorator in node.decorator_list:
            if self._is_cache_decorator(decorator):
                self.stats['cached_views'] += 1
                return

        # Check dispatch method
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == 'dispatch':
                if self._has_cache_decorator(item):
                    self.stats['cached_views'] += 1
                    return

        self.issues.append({
            'type': 'missing_cache',
            'severity': 'info',
            'location': f'{self.filepath}:{node.lineno}',
            'message': f'Class-based view "{node.name}" could benefit from caching',
            'suggestion': 'Consider adding @cache_page decorator to dispatch method'
        })

    def _check_expensive_queries(self, node: ast.FunctionDef):
        """Check for expensive database queries"""
        for stmt in ast.walk(node):
            # Check for .all()
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    # QuerySet methods that could be expensive
                    expensive_methods = ['all', 'filter', 'exclude', 'order_by']

                    if stmt.func.attr in expensive_methods:
                        self.stats['queries'] += 1

                        # Check if result is cached
                        parent = self._get_parent_assignment(node, stmt)
                        if parent and self._is_cached_assignment(parent):
                            self.stats['cached_queries'] += 1
                        else:
                            # Check for specific expensive patterns
                            if self._is_expensive_query(stmt):
                                self.issues.append({
                                    'type': 'expensive_query',
                                    'severity': 'warning',
                                    'location': f'{self.filepath}:{stmt.lineno}',
                                    'message': f'Expensive query detected: .{stmt.func.attr}()',
                                    'suggestion': 'Consider caching this query result'
                                })

                    # Check for aggregate operations
                    aggregate_methods = ['count', 'aggregate', 'annotate']
                    if stmt.func.attr in aggregate_methods:
                        self.issues.append({
                            'type': 'cacheable_aggregate',
                            'severity': 'info',
                            'location': f'{self.filepath}:{stmt.lineno}',
                            'message': f'Aggregate operation .{stmt.func.attr}() could be cached',
                            'suggestion': 'Consider caching this expensive aggregation'
                        })

    def _check_cache_operations(self, node: ast.FunctionDef):
        """Check for cache.set without corresponding cache.delete"""
        cache_sets = []
        cache_deletes = []

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if stmt.func.attr == 'set' and self._is_cache_object(stmt.func.value):
                        # Extract cache key if it's a string
                        if stmt.args and isinstance(stmt.args[0], ast.Str):
                            cache_sets.append(stmt.args[0].s)
                        elif stmt.args and isinstance(stmt.args[0], ast.Constant):
                            cache_sets.append(stmt.args[0].value)

                    elif stmt.func.attr == 'delete' and self._is_cache_object(stmt.func.value):
                        if stmt.args and isinstance(stmt.args[0], ast.Str):
                            cache_deletes.append(stmt.args[0].s)
                        elif stmt.args and isinstance(stmt.args[0], ast.Constant):
                            cache_deletes.append(stmt.args[0].value)

        # Check for sets without corresponding deletes in the file
        # This is a simple heuristic
        if cache_sets:
            self.stats['cache_invalidations'] += len(cache_deletes)

    def _check_model_caching(self, node: ast.ClassDef):
        """Check if model has proper cache invalidation"""
        has_save_override = False
        has_cache_invalidation = False

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == 'save':
                    has_save_override = True
                    # Check if it has cache invalidation
                    if self._contains_cache_operations(item):
                        has_cache_invalidation = True

        if has_save_override and not has_cache_invalidation:
            self.issues.append({
                'type': 'missing_invalidation',
                'severity': 'warning',
                'location': f'{self.filepath}:{node.lineno}',
                'message': f'Model "{node.name}" overrides save() but doesn\'t invalidate cache',
                'suggestion': 'Add cache invalidation in save() or use signals'
            })

    def _has_cache_decorator(self, node: ast.FunctionDef) -> bool:
        """Check if function has cache decorator"""
        for decorator in node.decorator_list:
            if self._is_cache_decorator(decorator):
                return True
        return False

    def _is_cache_decorator(self, decorator) -> bool:
        """Check if decorator is a caching decorator"""
        if isinstance(decorator, ast.Name):
            return decorator.id in ['cache_page', 'cache_control']
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id in ['cache_page', 'cache_control']
        return False

    def _contains_cache_operations(self, node) -> bool:
        """Check if node contains cache.get or cache.set calls"""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if stmt.func.attr in ['get', 'set', 'get_or_set', 'delete']:
                        if self._is_cache_object(stmt.func.value):
                            return True
        return False

    def _is_cache_object(self, node) -> bool:
        """Check if node refers to cache object"""
        if isinstance(node, ast.Name):
            return node.id == 'cache'
        elif isinstance(node, ast.Attribute):
            return node.attr == 'cache'
        return False

    def _get_parent_assignment(self, root, target_node):
        """Find assignment statement containing target node"""
        for node in ast.walk(root):
            if isinstance(node, ast.Assign):
                for child in ast.walk(node.value):
                    if child is target_node:
                        return node
        return None

    def _is_cached_assignment(self, assign_node: ast.Assign) -> bool:
        """Check if assignment is wrapped in cache.get_or_set"""
        # This is a simplified check
        return False

    def _is_expensive_query(self, call_node: ast.Call) -> bool:
        """Check if query is likely expensive"""
        # Check for missing select_related/prefetch_related
        # This is a heuristic - assumes queries without these are potentially expensive
        func = call_node.func

        if isinstance(func, ast.Attribute):
            # Check for chained calls
            if func.attr in ['all', 'filter']:
                # Look for select_related or prefetch_related in chain
                current = func.value
                while isinstance(current, ast.Call):
                    if isinstance(current.func, ast.Attribute):
                        if current.func.attr in ['select_related', 'prefetch_related']:
                            return False  # Has optimization
                    current = getattr(current.func, 'value', None)
                    if current is None:
                        break

                # No select_related found, likely expensive
                return True

        return False


def analyze_file(filepath: Path) -> Dict[str, Any]:
    """Analyze a Python file for caching issues"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        analyzer = DjangoCodeAnalyzer(str(filepath))
        analyzer.visit(tree)

        return {
            'filepath': str(filepath),
            'issues': analyzer.issues,
            'stats': analyzer.stats
        }

    except SyntaxError as e:
        return {
            'filepath': str(filepath),
            'error': f'Syntax error: {e}',
            'issues': [],
            'stats': {}
        }
    except Exception as e:
        return {
            'filepath': str(filepath),
            'error': f'Error: {e}',
            'issues': [],
            'stats': {}
        }


def find_python_files(directory: Path, app_name: str = None) -> List[Path]:
    """Find Python files in Django project"""
    files = []

    if app_name:
        # Look for specific app
        app_paths = [
            directory / app_name,
            directory / 'apps' / app_name,
        ]

        for app_path in app_paths:
            if app_path.exists():
                files.extend(app_path.rglob('*.py'))
                break
    else:
        # Find all Python files, excluding common non-app directories
        exclude_dirs = {'migrations', 'tests', '__pycache__', '.venv', 'venv', 'env'}

        for py_file in directory.rglob('*.py'):
            # Skip if in excluded directory
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue

            # Skip if not in an app-like structure
            if 'manage.py' in str(py_file):
                continue

            files.append(py_file)

    return files


def analyze_project(app_name: str = None, verbose: bool = False) -> Dict[str, Any]:
    """Analyze entire Django project"""
    # Find Django project root
    current_dir = Path.cwd()

    # Look for manage.py to confirm Django project
    if not (current_dir / 'manage.py').exists():
        # Try parent directory
        if (current_dir.parent / 'manage.py').exists():
            current_dir = current_dir.parent
        else:
            print("Error: Not in a Django project directory (manage.py not found)")
            return None

    if verbose:
        print(f"Analyzing Django project at: {current_dir}")

    # Find Python files
    python_files = find_python_files(current_dir, app_name)

    if verbose:
        print(f"Found {len(python_files)} Python files to analyze")

    # Analyze each file
    results = {
        'files_analyzed': 0,
        'total_issues': 0,
        'issues_by_severity': defaultdict(int),
        'issues_by_type': defaultdict(int),
        'total_stats': defaultdict(int),
        'file_results': []
    }

    for filepath in python_files:
        if verbose:
            print(f"Analyzing: {filepath}")

        result = analyze_file(filepath)

        if 'error' in result:
            if verbose:
                print(f"  Error: {result['error']}")
            continue

        results['files_analyzed'] += 1
        results['total_issues'] += len(result['issues'])

        for issue in result['issues']:
            results['issues_by_severity'][issue['severity']] += 1
            results['issues_by_type'][issue['type']] += 1

        for key, value in result['stats'].items():
            results['total_stats'][key] += value

        if result['issues']:
            results['file_results'].append(result)

    return results


def print_analysis_report(results: Dict[str, Any], verbose: bool = False):
    """Print analysis results"""
    if not results:
        return

    print("\n" + "=" * 70)
    print("Django Cache Analyzer Report")
    print("=" * 70)

    print(f"\nFiles Analyzed: {results['files_analyzed']}")
    print(f"Total Issues Found: {results['total_issues']}")

    if results['total_issues'] > 0:
        print("\nIssues by Severity:")
        for severity, count in results['issues_by_severity'].items():
            print(f"  {severity.upper()}: {count}")

        print("\nIssues by Type:")
        for issue_type, count in results['issues_by_type'].items():
            print(f"  {issue_type}: {count}")

    print("\nCaching Statistics:")
    stats = results['total_stats']
    print(f"  Total Views: {stats.get('views', 0)}")
    print(f"  Cached Views: {stats.get('cached_views', 0)}")
    if stats.get('views', 0) > 0:
        cache_rate = (stats.get('cached_views', 0) / stats.get('views', 0)) * 100
        print(f"  View Cache Rate: {cache_rate:.1f}%")

    print(f"\n  Total Queries Detected: {stats.get('queries', 0)}")
    print(f"  Cached Queries: {stats.get('cached_queries', 0)}")

    print(f"\n  Cache Invalidations Found: {stats.get('cache_invalidations', 0)}")

    if verbose and results['file_results']:
        print("\n" + "=" * 70)
        print("Detailed Issues")
        print("=" * 70)

        for file_result in results['file_results']:
            print(f"\n{file_result['filepath']}")
            print("-" * 70)

            for issue in file_result['issues']:
                print(f"\n  [{issue['severity'].upper()}] {issue['type']}")
                print(f"  Location: {issue['location']}")
                print(f"  Message: {issue['message']}")
                print(f"  Suggestion: {issue['suggestion']}")

    print("\n" + "=" * 70)
    print("Recommendations:")
    print("=" * 70)

    if results['total_issues'] == 0:
        print("✓ Great! No obvious caching issues found.")
    else:
        print("\n1. Add caching to frequently accessed views")
        print("2. Cache expensive database queries")
        print("3. Implement proper cache invalidation")
        print("4. Use select_related/prefetch_related to optimize queries")
        print("5. Review cache timeouts for your use case")


def check_invalidation_issues(app_name: str = None) -> Dict[str, Any]:
    """Check for cache invalidation issues"""
    print("\nChecking for cache invalidation issues...")

    current_dir = Path.cwd()
    python_files = find_python_files(current_dir, app_name)

    issues = []

    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for cache.set without cache.delete
            has_cache_set = 'cache.set' in content or 'cache.get_or_set' in content
            has_cache_delete = 'cache.delete' in content
            has_signal = '@receiver' in content or 'post_save' in content

            if has_cache_set and not has_cache_delete and not has_signal:
                issues.append({
                    'file': str(filepath),
                    'issue': 'Uses cache.set but no invalidation logic found',
                    'suggestion': 'Add cache.delete calls or use signals for invalidation'
                })

        except Exception as e:
            continue

    return {'issues': issues}


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze Django code for caching opportunities'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze code for caching issues')
    analyze_parser.add_argument('--app', help='Specific app to analyze')
    analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # Check invalidation command
    invalidation_parser = subparsers.add_parser(
        'check-invalidation',
        help='Check for cache invalidation issues'
    )
    invalidation_parser.add_argument('--app', help='Specific app to analyze')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate JSON report')
    report_parser.add_argument('--output', '-o', help='Output file', default='cache_report.json')
    report_parser.add_argument('--app', help='Specific app to analyze')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'analyze':
        results = analyze_project(app_name=args.app, verbose=args.verbose)
        if results:
            print_analysis_report(results, verbose=args.verbose)

    elif args.command == 'check-invalidation':
        results = check_invalidation_issues(app_name=args.app)
        print("\n" + "=" * 70)
        print("Cache Invalidation Issues")
        print("=" * 70)

        if not results['issues']:
            print("\n✓ No obvious cache invalidation issues found.")
        else:
            for issue in results['issues']:
                print(f"\nFile: {issue['file']}")
                print(f"Issue: {issue['issue']}")
                print(f"Suggestion: {issue['suggestion']}")

    elif args.command == 'report':
        results = analyze_project(app_name=args.app, verbose=False)
        if results:
            # Convert defaultdict to dict for JSON serialization
            results['issues_by_severity'] = dict(results['issues_by_severity'])
            results['issues_by_type'] = dict(results['issues_by_type'])
            results['total_stats'] = dict(results['total_stats'])

            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"\nReport saved to: {args.output}")
            print(f"Files analyzed: {results['files_analyzed']}")
            print(f"Issues found: {results['total_issues']}")


if __name__ == '__main__':
    main()
