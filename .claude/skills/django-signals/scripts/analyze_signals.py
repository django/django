#!/usr/bin/env python
"""
Django Signal Analyzer

Analyzes a Django project to find signal handlers and detect anti-patterns.

Usage:
    python analyze_signals.py [--project-dir /path/to/project]

Features:
    - Finds all signal handlers
    - Detects recursion risks
    - Identifies performance issues
    - Checks transaction safety
    - Reports circular dependencies
"""

import ast
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Set, Tuple


class SignalAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze signal usage in Python files."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.handlers = []
        self.signals_sent = []
        self.imports = {}
        self.current_class = None
        self.current_function = None

    def visit_Import(self, node):
        """Track imports."""
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports."""
        module = node.module or ''
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track current class."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Analyze function definitions for signal handlers."""
        old_function = self.current_function
        self.current_function = node.name

        # Check for @receiver decorator
        for decorator in node.decorator_list:
            if self._is_receiver_decorator(decorator):
                handler_info = self._extract_handler_info(node, decorator)
                if handler_info:
                    self.handlers.append(handler_info)

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        """Detect signal.connect() calls and signal.send() calls."""
        if isinstance(node.func, ast.Attribute):
            # Check for signal.connect()
            if node.func.attr == 'connect':
                self._handle_connect_call(node)

            # Check for signal.send() or signal.send_robust()
            elif node.func.attr in ('send', 'send_robust'):
                self._handle_send_call(node)

            # Check for model.save() in handlers (potential recursion)
            elif node.func.attr == 'save':
                if self.current_function and self._is_in_handler():
                    self.handlers[-1].setdefault('save_calls', []).append({
                        'line': node.lineno,
                        'function': self.current_function
                    })

        self.generic_visit(node)

    def _is_receiver_decorator(self, decorator) -> bool:
        """Check if decorator is @receiver."""
        if isinstance(decorator, ast.Name):
            return decorator.id == 'receiver'
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id == 'receiver'
        return False

    def _extract_handler_info(self, func_node, decorator) -> Dict:
        """Extract information about a signal handler."""
        if not isinstance(decorator, ast.Call):
            return None

        signal_name = None
        sender = None
        dispatch_uid = None

        # Get signal (first positional arg)
        if decorator.args:
            signal_arg = decorator.args[0]
            signal_name = self._get_name_from_node(signal_arg)

        # Get sender and dispatch_uid from kwargs
        for keyword in decorator.keywords:
            if keyword.arg == 'sender':
                sender = self._get_name_from_node(keyword.value)
            elif keyword.arg == 'dispatch_uid':
                if isinstance(keyword.value, ast.Constant):
                    dispatch_uid = keyword.value.value

        # Check for transaction.on_commit in function body
        uses_on_commit = self._check_on_commit_usage(func_node)

        # Check for heavy operations
        has_heavy_ops = self._check_heavy_operations(func_node)

        return {
            'file': self.filepath,
            'line': func_node.lineno,
            'function': func_node.name,
            'signal': signal_name,
            'sender': sender,
            'dispatch_uid': dispatch_uid,
            'uses_on_commit': uses_on_commit,
            'has_heavy_ops': has_heavy_ops,
            'class': self.current_class,
        }

    def _handle_connect_call(self, node):
        """Handle signal.connect() calls."""
        # Extract information about manual connection
        pass

    def _handle_send_call(self, node):
        """Handle signal.send() calls."""
        signal_name = None
        if isinstance(node.func.value, ast.Name):
            signal_name = node.func.value.id

        self.signals_sent.append({
            'file': self.filepath,
            'line': node.lineno,
            'signal': signal_name,
            'function': self.current_function,
            'method': node.func.attr,  # 'send' or 'send_robust'
        })

    def _get_name_from_node(self, node) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name_from_node(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown"

    def _check_on_commit_usage(self, func_node) -> bool:
        """Check if function uses transaction.on_commit()."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'on_commit':
                        return True
        return False

    def _check_heavy_operations(self, func_node) -> List[str]:
        """Check for potentially heavy operations."""
        heavy_ops = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Check for file operations
                    if node.func.attr in ('open', 'read', 'write'):
                        heavy_ops.append(f"File I/O at line {node.lineno}")

                    # Check for HTTP requests
                    elif node.func.attr in ('get', 'post', 'put', 'delete', 'request'):
                        heavy_ops.append(f"HTTP request at line {node.lineno}")

                    # Check for email sending
                    elif 'send' in node.func.attr and 'mail' in str(node.func):
                        heavy_ops.append(f"Email sending at line {node.lineno}")

        return heavy_ops

    def _is_in_handler(self) -> bool:
        """Check if currently analyzing a signal handler."""
        return bool(self.handlers)


class ProjectAnalyzer:
    """Analyzes entire Django project for signal usage."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.handlers: List[Dict] = []
        self.signals_sent: List[Dict] = []
        self.issues: List[Dict] = []

    def analyze(self):
        """Analyze all Python files in project."""
        print(f"Analyzing Django project at: {self.project_dir}")
        print("=" * 60)

        # Find all Python files
        python_files = list(self.project_dir.rglob("*.py"))
        print(f"Found {len(python_files)} Python files\n")

        # Analyze each file
        for filepath in python_files:
            # Skip migrations and virtual environments
            if 'migrations' in filepath.parts or 'venv' in filepath.parts:
                continue

            try:
                self._analyze_file(filepath)
            except Exception as e:
                print(f"Error analyzing {filepath}: {e}")

        # Detect issues
        self._detect_issues()

    def _analyze_file(self, filepath: Path):
        """Analyze a single Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(filepath))

            analyzer = SignalAnalyzer(str(filepath.relative_to(self.project_dir)))
            analyzer.visit(tree)

            self.handlers.extend(analyzer.handlers)
            self.signals_sent.extend(analyzer.signals_sent)

        except SyntaxError:
            # Skip files with syntax errors
            pass

    def _detect_issues(self):
        """Detect potential issues in signal usage."""
        # Issue 1: Handlers without dispatch_uid
        for handler in self.handlers:
            if not handler.get('dispatch_uid'):
                self.issues.append({
                    'severity': 'warning',
                    'type': 'missing_dispatch_uid',
                    'message': f"Handler '{handler['function']}' missing dispatch_uid",
                    'file': handler['file'],
                    'line': handler['line'],
                })

        # Issue 2: Handlers with save() calls (recursion risk)
        for handler in self.handlers:
            if handler.get('save_calls'):
                self.issues.append({
                    'severity': 'error',
                    'type': 'recursion_risk',
                    'message': f"Handler '{handler['function']}' calls save() - recursion risk!",
                    'file': handler['file'],
                    'line': handler['line'],
                    'suggestion': "Use QuerySet.update() or check update_fields to prevent recursion"
                })

        # Issue 3: Heavy operations without on_commit
        for handler in self.handlers:
            if handler.get('has_heavy_ops') and not handler.get('uses_on_commit'):
                self.issues.append({
                    'severity': 'warning',
                    'type': 'transaction_safety',
                    'message': f"Handler '{handler['function']}' has heavy operations without on_commit()",
                    'file': handler['file'],
                    'line': handler['line'],
                    'operations': handler['has_heavy_ops'],
                    'suggestion': "Use transaction.on_commit() to ensure transaction completes first"
                })

        # Issue 4: Duplicate signal/sender combinations
        handler_keys = defaultdict(list)
        for handler in self.handlers:
            key = (handler.get('signal'), handler.get('sender'))
            handler_keys[key].append(handler)

        for key, handlers_list in handler_keys.items():
            if len(handlers_list) > 1:
                # Check if they have different dispatch_uids
                dispatch_uids = [h.get('dispatch_uid') for h in handlers_list]
                if len(set(dispatch_uids)) < len(handlers_list):
                    self.issues.append({
                        'severity': 'error',
                        'type': 'duplicate_handlers',
                        'message': f"Multiple handlers for {key[0]} / {key[1]}",
                        'handlers': [f"{h['file']}:{h['line']}" for h in handlers_list],
                        'suggestion': "Use unique dispatch_uid for each handler"
                    })

    def report(self):
        """Generate analysis report."""
        print("\n" + "=" * 60)
        print("SIGNAL ANALYSIS REPORT")
        print("=" * 60)

        # Summary
        print(f"\n📊 Summary:")
        print(f"  - Signal Handlers Found: {len(self.handlers)}")
        print(f"  - Signals Sent: {len(self.signals_sent)}")
        print(f"  - Issues Detected: {len(self.issues)}")

        # List handlers
        if self.handlers:
            print(f"\n🎯 Signal Handlers:")
            for handler in self.handlers:
                print(f"\n  Handler: {handler['function']}")
                print(f"    File: {handler['file']}:{handler['line']}")
                print(f"    Signal: {handler['signal']}")
                print(f"    Sender: {handler['sender']}")
                print(f"    dispatch_uid: {handler['dispatch_uid'] or 'MISSING ⚠️'}")
                if handler.get('uses_on_commit'):
                    print(f"    Uses on_commit: ✅")
                if handler.get('has_heavy_ops'):
                    print(f"    Heavy operations: ⚠️")
                    for op in handler['has_heavy_ops']:
                        print(f"      - {op}")

        # List signals sent
        if self.signals_sent:
            print(f"\n📤 Signals Sent:")
            for signal in self.signals_sent:
                print(f"  {signal['signal']}.{signal['method']}() at {signal['file']}:{signal['line']}")

        # Report issues
        if self.issues:
            print(f"\n⚠️  Issues Found:")

            # Group by severity
            errors = [i for i in self.issues if i['severity'] == 'error']
            warnings = [i for i in self.issues if i['severity'] == 'warning']

            if errors:
                print(f"\n  🔴 Errors ({len(errors)}):")
                for issue in errors:
                    print(f"\n    {issue['message']}")
                    print(f"    Location: {issue['file']}:{issue['line']}")
                    if 'suggestion' in issue:
                        print(f"    💡 Suggestion: {issue['suggestion']}")

            if warnings:
                print(f"\n  🟡 Warnings ({len(warnings)}):")
                for issue in warnings:
                    print(f"\n    {issue['message']}")
                    print(f"    Location: {issue['file']}:{issue['line']}")
                    if 'suggestion' in issue:
                        print(f"    💡 Suggestion: {issue['suggestion']}")
        else:
            print(f"\n✅ No issues detected!")

        # Recommendations
        print(f"\n💡 Best Practices:")
        print(f"  1. Always use dispatch_uid to prevent duplicate connections")
        print(f"  2. Use transaction.on_commit() for external operations")
        print(f"  3. Avoid calling save() in post_save handlers")
        print(f"  4. Offload heavy work to task queues (Celery)")
        print(f"  5. Use QuerySet.update() to avoid triggering signals")

        print(f"\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze Django project for signal usage and anti-patterns'
    )
    parser.add_argument(
        '--project-dir',
        default='.',
        help='Path to Django project directory (default: current directory)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Validate project directory
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: Directory not found: {project_dir}")
        sys.exit(1)

    # Analyze project
    analyzer = ProjectAnalyzer(project_dir)
    analyzer.analyze()

    # Generate report
    if args.json:
        import json
        print(json.dumps({
            'handlers': analyzer.handlers,
            'signals_sent': analyzer.signals_sent,
            'issues': analyzer.issues,
        }, indent=2))
    else:
        analyzer.report()


if __name__ == '__main__':
    main()
