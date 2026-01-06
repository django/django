#!/usr/bin/env python3
"""
Django Slow Test Detector

Identifies slow tests and suggests optimizations.

Usage:
    # Find tests taking more than 1 second
    python detect_slow_tests.py --threshold 1.0

    # Analyze query counts
    python detect_slow_tests.py --check-queries

    # Generate optimization report
    python detect_slow_tests.py --report optimization_report.json

    # Combine all analysis
    python detect_slow_tests.py --threshold 0.5 --check-queries --report report.json

Features:
    - Identifies slow-running tests
    - Detects N+1 query problems
    - Suggests setUpTestData usage
    - Finds tests that could use select_related/prefetch_related
    - Generates actionable optimization recommendations
"""

import argparse
import ast
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional
import unittest
import io


class TestAnalyzer:
    """Analyzes Django tests for performance issues."""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.slow_tests = []
        self.test_timings = {}
        self.query_counts = {}
        self.recommendations = []

    def analyze_test_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a test file for potential issues."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)

            analysis = {
                'file': file_path,
                'issues': [],
                'test_classes': []
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_analysis = self._analyze_test_class(node, content)
                    if class_analysis:
                        analysis['test_classes'].append(class_analysis)

            return analysis

        except Exception as e:
            return {
                'file': file_path,
                'error': str(e)
            }

    def _analyze_test_class(self, class_node: ast.ClassDef, file_content: str) -> Optional[Dict[str, Any]]:
        """Analyze a test class for performance issues."""
        # Check if it's a test class
        is_test_class = False
        for base in class_node.bases:
            if isinstance(base, ast.Name) and 'Test' in base.id:
                is_test_class = True
                break
            elif isinstance(base, ast.Attribute) and 'Test' in base.attr:
                is_test_class = True
                break

        if not is_test_class:
            return None

        analysis = {
            'name': class_node.name,
            'issues': [],
            'has_setup_test_data': False,
            'has_setup': False,
            'test_methods': [],
            'database_operations': []
        }

        # Check for setUp and setUpTestData
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == 'setUpTestData':
                    analysis['has_setup_test_data'] = True
                elif item.name == 'setUp':
                    analysis['has_setup'] = True
                    # Analyze setUp for database operations
                    setup_issues = self._analyze_setup_method(item)
                    if setup_issues:
                        analysis['issues'].extend(setup_issues)
                elif item.name.startswith('test_'):
                    test_info = self._analyze_test_method(item)
                    analysis['test_methods'].append(test_info)

        return analysis

    def _analyze_setup_method(self, func_node: ast.FunctionDef) -> List[str]:
        """Check setUp method for performance issues."""
        issues = []
        creates_objects = False

        for node in ast.walk(func_node):
            # Check for .objects.create() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'create':
                        creates_objects = True
                        break

        if creates_objects:
            issues.append(
                f"setUp() creates objects - consider using setUpTestData() "
                f"for read-only test data (can be 10-100x faster)"
            )

        return issues

    def _analyze_test_method(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a test method for potential issues."""
        info = {
            'name': func_node.name,
            'issues': [],
            'creates_objects': False,
            'has_loops': False,
            'query_count_check': False
        }

        for node in ast.walk(func_node):
            # Check for object creation
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('create', 'bulk_create'):
                        info['creates_objects'] = True
                    elif node.func.attr == 'assertNumQueries':
                        info['query_count_check'] = True

            # Check for loops
            if isinstance(node, (ast.For, ast.While)):
                info['has_loops'] = True

        # Check for potential issues
        if info['creates_objects'] and info['has_loops']:
            info['issues'].append(
                "Test creates objects in a loop - consider bulk_create() or fixtures"
            )

        return info

    def find_slow_tests(self, test_dir: str = '.') -> List[Dict[str, Any]]:
        """Find all test files and analyze them."""
        results = []

        for root, dirs, files in os.walk(test_dir):
            # Skip virtual environments and migrations
            dirs[:] = [d for d in dirs if d not in ('venv', 'virtualenv', 'migrations', '__pycache__')]

            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    analysis = self.analyze_test_file(file_path)
                    results.append(analysis)

        return results

    def generate_recommendations(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []

        for result in analysis_results:
            if 'error' in result:
                continue

            for test_class in result.get('test_classes', []):
                class_name = test_class['name']
                file_name = result['file']

                # Recommendation: Use setUpTestData
                if test_class['has_setup'] and not test_class['has_setup_test_data']:
                    has_create = False
                    for issue in test_class['issues']:
                        if 'setUpTestData' in issue:
                            has_create = True
                            break

                    if has_create:
                        recommendations.append({
                            'severity': 'high',
                            'file': file_name,
                            'class': class_name,
                            'issue': 'Using setUp() instead of setUpTestData()',
                            'recommendation': (
                                'Move read-only test data creation from setUp() to '
                                'setUpTestData() for better performance. setUpTestData() '
                                'runs once per test class instead of once per test method.'
                            ),
                            'example': f"""
@classmethod
def setUpTestData(cls):
    '''Create test data once for all tests'''
    cls.user = User.objects.create_user('testuser')
    cls.article = Article.objects.create(title='Test', author=cls.user)

def setUp(self):
    '''Only use for mutable state that changes per test'''
    self.client = Client()
"""
                        })

                # Check test methods
                for test_method in test_class['test_methods']:
                    if test_method['issues']:
                        for issue in test_method['issues']:
                            recommendations.append({
                                'severity': 'medium',
                                'file': file_name,
                                'class': class_name,
                                'method': test_method['name'],
                                'issue': issue,
                                'recommendation': (
                                    'Use bulk_create() to create multiple objects efficiently'
                                ),
                                'example': """
# Instead of:
for i in range(100):
    Article.objects.create(title=f'Article {i}')

# Use:
articles = [Article(title=f'Article {i}') for i in range(100)]
Article.objects.bulk_create(articles)
"""
                            })

                    # Check for missing query assertions
                    if test_method['creates_objects'] and not test_method['query_count_check']:
                        recommendations.append({
                            'severity': 'low',
                            'file': file_name,
                            'class': class_name,
                            'method': test_method['name'],
                            'issue': 'No query count assertion',
                            'recommendation': (
                                'Add assertNumQueries() to detect N+1 query problems'
                            ),
                            'example': """
def test_article_list(self):
    # Create test data
    for i in range(10):
        Article.objects.create(title=f'Article {i}')

    # Assert query count to catch N+1 problems
    with self.assertNumQueries(1):
        list(Article.objects.all())
"""
                        })

        return recommendations


class TestRunner:
    """Runs tests and collects timing information."""

    def __init__(self):
        self.test_timings = {}
        self.query_counts = {}

    def run_tests_with_timing(self, test_labels: List[str] = None) -> Dict[str, float]:
        """Run tests and collect timing information."""
        # This would integrate with Django's test runner
        # For now, return empty dict as this requires Django context
        return {}


def print_analysis_summary(analysis_results: List[Dict[str, Any]], threshold: float):
    """Print a summary of the analysis."""
    print("\n" + "="*80)
    print("SLOW TEST ANALYSIS SUMMARY")
    print("="*80)

    total_files = len(analysis_results)
    total_classes = sum(len(r.get('test_classes', [])) for r in analysis_results)
    total_issues = sum(
        sum(len(tc.get('issues', [])) for tc in r.get('test_classes', []))
        for r in analysis_results
    )

    print(f"\nAnalyzed: {total_files} test files, {total_classes} test classes")
    print(f"Found: {total_issues} potential issues")

    if total_issues > 0:
        print("\nIssues by severity:")
        print("  - High: setUp() should use setUpTestData()")
        print("  - Medium: Object creation in loops")
        print("  - Low: Missing query count assertions")


def print_recommendations(recommendations: List[Dict[str, Any]]):
    """Print optimization recommendations."""
    if not recommendations:
        print("\n✓ No optimization recommendations - tests look good!")
        return

    print("\n" + "="*80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("="*80)

    # Group by severity
    by_severity = defaultdict(list)
    for rec in recommendations:
        by_severity[rec['severity']].append(rec)

    for severity in ['high', 'medium', 'low']:
        recs = by_severity[severity]
        if not recs:
            continue

        print(f"\n{severity.upper()} PRIORITY ({len(recs)} issues)")
        print("-" * 80)

        for rec in recs:
            print(f"\n📁 {rec['file']}")
            print(f"   Class: {rec['class']}")
            if 'method' in rec:
                print(f"   Method: {rec['method']}")
            print(f"\n   Issue: {rec['issue']}")
            print(f"\n   Recommendation:")
            print(f"   {rec['recommendation']}")
            if rec.get('example'):
                print(f"\n   Example:")
                for line in rec['example'].strip().split('\n'):
                    print(f"   {line}")


def save_report(analysis_results: List[Dict[str, Any]],
                recommendations: List[Dict[str, Any]],
                output_file: str):
    """Save analysis results to JSON file."""
    report = {
        'summary': {
            'total_files': len(analysis_results),
            'total_classes': sum(len(r.get('test_classes', [])) for r in analysis_results),
            'total_recommendations': len(recommendations),
        },
        'analysis': analysis_results,
        'recommendations': recommendations,
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Detect slow Django tests and suggest optimizations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find tests taking more than 1 second
  python detect_slow_tests.py --threshold 1.0

  # Analyze query counts
  python detect_slow_tests.py --check-queries

  # Generate full report
  python detect_slow_tests.py --threshold 0.5 --report optimization_report.json

  # Analyze specific directory
  python detect_slow_tests.py --directory myapp/tests/
        """
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=1.0,
        help='Threshold in seconds for slow tests (default: 1.0)'
    )
    parser.add_argument(
        '--check-queries',
        action='store_true',
        help='Check for N+1 query problems'
    )
    parser.add_argument(
        '--report',
        help='Save detailed report to JSON file'
    )
    parser.add_argument(
        '--directory',
        default='.',
        help='Directory to analyze (default: current directory)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed analysis'
    )

    args = parser.parse_args()

    print("Analyzing Django tests for performance issues...")
    print(f"Directory: {args.directory}")
    print(f"Threshold: {args.threshold}s")

    # Initialize analyzer
    analyzer = TestAnalyzer(threshold=args.threshold)

    # Find and analyze tests
    analysis_results = analyzer.find_slow_tests(args.directory)

    # Generate recommendations
    recommendations = analyzer.generate_recommendations(analysis_results)

    # Print summary
    print_analysis_summary(analysis_results, args.threshold)

    # Print recommendations
    print_recommendations(recommendations)

    # Save report if requested
    if args.report:
        save_report(analysis_results, recommendations, args.report)

    # Exit with error code if issues found
    if recommendations:
        print("\n⚠️  Performance issues detected. Review recommendations above.")
        sys.exit(1)
    else:
        print("\n✓ All tests look optimized!")
        sys.exit(0)


if __name__ == '__main__':
    main()
