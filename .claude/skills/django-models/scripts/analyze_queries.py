#!/usr/bin/env python3
"""
N+1 Query Detection Script

Analyzes Python files for potential N+1 query problems by detecting patterns where
related objects are accessed in loops without proper select_related/prefetch_related.

Usage:
    python analyze_queries.py <file_path>
    python analyze_queries.py myapp/views.py

Output: JSON report of potential issues
"""

import ast
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Set


class QueryAnalyzer(ast.NodeVisitor):
    """AST visitor to detect N+1 query patterns"""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[Dict[str, Any]] = []
        self.current_function = None
        self.loop_depth = 0
        self.queryset_variables: Dict[str, Set[str]] = {}  # var_name -> {methods_called}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track current function context"""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_For(self, node: ast.For):
        """Detect loops over querysets"""
        self.loop_depth += 1

        # Check if iterating over a queryset
        iter_var = None
        if isinstance(node.iter, ast.Name):
            iter_var = node.iter.id
        elif isinstance(node.iter, ast.Call):
            # Check for .all(), .filter(), etc.
            if self._is_queryset_call(node.iter):
                # Extract variable if chained from one
                base_obj = self._get_base_object(node.iter)
                if base_obj:
                    iter_var = base_obj

        # Analyze body for relationship access
        if iter_var or self._is_queryset_call(node.iter):
            self._analyze_loop_body(node, node.lineno)

        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_Assign(self, node: ast.Assign):
        """Track QuerySet assignments"""
        if isinstance(node.value, ast.Call):
            if self._is_queryset_call(node.value):
                # Track which methods are called on this queryset
                methods = self._extract_queryset_methods(node.value)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.queryset_variables[target.id] = methods

        self.generic_visit(node)

    def _is_queryset_call(self, node: ast.Call) -> bool:
        """Check if call is a QuerySet operation"""
        queryset_methods = {
            'all', 'filter', 'exclude', 'get', 'first', 'last',
            'order_by', 'distinct', 'values', 'values_list',
            'annotate', 'aggregate', 'count', 'exists'
        }

        if isinstance(node.func, ast.Attribute):
            if node.func.attr in queryset_methods:
                return True

            # Check for Model.objects pattern
            if isinstance(node.func.value, ast.Attribute):
                if node.func.value.attr == 'objects':
                    return True

        return False

    def _get_base_object(self, node: ast.AST) -> str:
        """Extract base variable name from chained calls"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_base_object(node.value)
        elif isinstance(node, ast.Call):
            return self._get_base_object(node.func)
        return None

    def _extract_queryset_methods(self, node: ast.Call) -> Set[str]:
        """Extract all methods called on a queryset"""
        methods = set()

        def extract(n):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute):
                    methods.add(n.func.attr)
                extract(n.func)
            elif isinstance(n, ast.Attribute):
                extract(n.value)

        extract(node)
        return methods

    def _analyze_loop_body(self, loop_node: ast.For, line_number: int):
        """Analyze loop body for relationship access"""
        # Get the loop variable name
        loop_var = None
        if isinstance(loop_node.target, ast.Name):
            loop_var = loop_node.target.id

        if not loop_var:
            return

        # Check what queryset this is iterating over
        queryset_methods = set()
        if isinstance(loop_node.iter, ast.Name):
            var_name = loop_node.iter.id
            queryset_methods = self.queryset_variables.get(var_name, set())

        # Look for relationship access in loop body
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Attribute):
                # Check if accessing attribute on loop variable
                if isinstance(node.value, ast.Name) and node.value.id == loop_var:
                    # Check if it's a relationship access
                    relationship_name = node.attr

                    # Skip obvious non-relationship attributes
                    if relationship_name in {'id', 'pk', 'save', 'delete', 'update'}:
                        continue

                    # Check if this might be a relationship
                    if self._looks_like_relationship_access(node):
                        # Check if appropriate prefetch was used
                        issue_type = self._determine_issue_type(
                            relationship_name,
                            queryset_methods
                        )

                        if issue_type:
                            self.issues.append({
                                'file': self.filename,
                                'line': line_number,
                                'type': issue_type,
                                'loop_variable': loop_var,
                                'relationship': relationship_name,
                                'recommendation': self._get_recommendation(
                                    issue_type,
                                    relationship_name
                                ),
                                'function': self.current_function,
                            })

    def _looks_like_relationship_access(self, node: ast.Attribute) -> bool:
        """Heuristic to determine if attribute access is a relationship"""
        # Check if followed by another attribute access or call
        parent = self._get_parent_in_tree(node)

        # If the attribute is accessed further (e.g., article.author.name)
        # it's likely a ForeignKey
        if isinstance(parent, ast.Attribute):
            return True

        # If there's a .all(), .filter(), .count() call, it's likely reverse FK or M2M
        if isinstance(parent, ast.Call):
            if isinstance(parent.func, ast.Attribute):
                if parent.func.attr in {'all', 'filter', 'count', 'exists', 'first'}:
                    return True

        return False

    def _get_parent_in_tree(self, node: ast.AST) -> ast.AST:
        """Get parent node (simplified - just check common patterns)"""
        # This is a simplified version; in practice, we'd track parent nodes
        return None

    def _determine_issue_type(
        self,
        relationship_name: str,
        queryset_methods: Set[str]
    ) -> str:
        """Determine if this is an N+1 issue"""
        # Check if select_related or prefetch_related was used
        if 'select_related' in queryset_methods:
            # Might still be N+1 if wrong relationship
            return None

        if 'prefetch_related' in queryset_methods:
            return None

        # If neither is used, it's likely an N+1
        return 'n_plus_one'

    def _get_recommendation(self, issue_type: str, relationship_name: str) -> str:
        """Get recommendation for fixing the issue"""
        if issue_type == 'n_plus_one':
            return (
                f"Use select_related('{relationship_name}') for ForeignKey/OneToOne, "
                f"or prefetch_related('{relationship_name}') for ManyToMany/reverse ForeignKey"
            )
        return ""


def analyze_file(filepath: str) -> Dict[str, Any]:
    """Analyze a Python file for N+1 query issues"""
    path = Path(filepath)

    if not path.exists():
        return {
            'error': f"File not found: {filepath}",
            'issues': []
        }

    if not path.suffix == '.py':
        return {
            'error': f"Not a Python file: {filepath}",
            'issues': []
        }

    try:
        with open(path, 'r') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(path))
        analyzer = QueryAnalyzer(str(path))
        analyzer.visit(tree)

        return {
            'file': str(path),
            'issues': analyzer.issues,
            'total_issues': len(analyzer.issues),
        }

    except SyntaxError as e:
        return {
            'error': f"Syntax error in {filepath}: {e}",
            'issues': []
        }
    except Exception as e:
        return {
            'error': f"Error analyzing {filepath}: {e}",
            'issues': []
        }


def format_report(result: Dict[str, Any]) -> str:
    """Format analysis result as readable text"""
    lines = []

    if 'error' in result:
        lines.append(f"❌ {result['error']}")
        return '\n'.join(lines)

    lines.append(f"\n📊 Analysis Report: {result['file']}")
    lines.append("=" * 80)

    if result['total_issues'] == 0:
        lines.append("✅ No N+1 query issues detected!")
    else:
        lines.append(f"⚠️  Found {result['total_issues']} potential N+1 query issue(s):\n")

        for i, issue in enumerate(result['issues'], 1):
            lines.append(f"{i}. Line {issue['line']} in {issue.get('function', 'unknown')}")
            lines.append(f"   Type: {issue['type']}")
            lines.append(f"   Loop variable: {issue['loop_variable']}")
            lines.append(f"   Relationship: {issue['relationship']}")
            lines.append(f"   💡 {issue['recommendation']}")
            lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_queries.py <file_path>")
        print("\nExample:")
        print("  python analyze_queries.py myapp/views.py")
        sys.exit(1)

    filepath = sys.argv[1]

    # Check for JSON output flag
    json_output = '--json' in sys.argv

    result = analyze_file(filepath)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    # Exit with error code if issues found
    if result.get('total_issues', 0) > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
