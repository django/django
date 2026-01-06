#!/usr/bin/env python
"""
Django Template Analyzer

Analyzes Django templates for:
- Unused templates
- Missing blocks in inheritance chains
- Template inheritance structure
- Performance issues (N+1 queries, missing cache)
- Template complexity metrics

Usage:
    python template_analyzer.py --find-unused
    python template_analyzer.py --check-blocks templates/
    python template_analyzer.py --check-performance templates/
    python template_analyzer.py --show-inheritance templates/base.html
    python template_analyzer.py --metrics templates/
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Set, Dict, Optional


@dataclass
class TemplateInfo:
    """Information about a template."""
    path: Path
    extends: Optional[str] = None
    includes: List[str] = None
    blocks: Set[str] = None
    loads: Set[str] = None
    queries_potential: int = 0
    cached_fragments: int = 0
    complexity_score: int = 0

    def __post_init__(self):
        if self.includes is None:
            self.includes = []
        if self.blocks is None:
            self.blocks = set()
        if self.loads is None:
            self.loads = set()


class TemplateAnalyzer:
    """Analyze Django templates."""

    # Regex patterns
    EXTENDS_PATTERN = re.compile(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}')
    INCLUDE_PATTERN = re.compile(r'{%\s*include\s+["\']([^"\']+)["\']\s*%}')
    BLOCK_PATTERN = re.compile(r'{%\s*block\s+(\w+)\s*%}')
    LOAD_PATTERN = re.compile(r'{%\s*load\s+([^%]+)%}')
    CACHE_PATTERN = re.compile(r'{%\s*cache\s+')
    FOR_LOOP_PATTERN = re.compile(r'{%\s*for\s+\w+\s+in\s+([^%]+)%}')
    QUERY_PATTERN = re.compile(r'{{[^}]*\.(all|filter|get|count|exists)\s*[^}]*}}')
    NESTED_ACCESS_PATTERN = re.compile(r'{{[^}]*\.\w+\.\w+[^}]*}}')

    def __init__(self, template_dirs: List[Path]):
        self.template_dirs = [Path(d) for d in template_dirs]
        self.templates: Dict[str, TemplateInfo] = {}
        self.referenced_templates: Set[str] = set()

    def find_templates(self) -> List[Path]:
        """Find all template files."""
        templates = []
        for template_dir in self.template_dirs:
            if not template_dir.exists():
                print(f"Warning: Template directory {template_dir} does not exist", file=sys.stderr)
                continue
            templates.extend(template_dir.rglob('*.html'))
        return templates

    def analyze_template(self, template_path: Path) -> TemplateInfo:
        """Analyze a single template."""
        try:
            content = template_path.read_text()
        except Exception as e:
            print(f"Error reading {template_path}: {e}", file=sys.stderr)
            return TemplateInfo(path=template_path)

        info = TemplateInfo(path=template_path)

        # Find extends
        extends_match = self.EXTENDS_PATTERN.search(content)
        if extends_match:
            info.extends = extends_match.group(1)
            self.referenced_templates.add(extends_match.group(1))

        # Find includes
        for match in self.INCLUDE_PATTERN.finditer(content):
            template_name = match.group(1)
            info.includes.append(template_name)
            self.referenced_templates.add(template_name)

        # Find blocks
        for match in self.BLOCK_PATTERN.finditer(content):
            info.blocks.add(match.group(1))

        # Find loads
        for match in self.LOAD_PATTERN.finditer(content):
            libraries = match.group(1).strip().split()
            info.loads.update(libraries)

        # Count cached fragments
        info.cached_fragments = len(self.CACHE_PATTERN.findall(content))

        # Detect potential query issues
        info.queries_potential = self._detect_query_issues(content)

        # Calculate complexity score
        info.complexity_score = self._calculate_complexity(content, info)

        return info

    def _detect_query_issues(self, content: str) -> int:
        """Detect potential N+1 query issues."""
        issues = 0

        # Find for loops
        for_loops = self.FOR_LOOP_PATTERN.findall(content)

        # Check for nested attribute access in loops (potential N+1)
        if for_loops:
            # Simplified check: count potential query methods
            issues += len(self.QUERY_PATTERN.findall(content))
            # Count nested attribute access
            issues += len(self.NESTED_ACCESS_PATTERN.findall(content))

        return issues

    def _calculate_complexity(self, content: str, info: TemplateInfo) -> int:
        """Calculate template complexity score."""
        score = 0

        # Count control flow
        score += len(re.findall(r'{%\s*if\s+', content)) * 1
        score += len(re.findall(r'{%\s*for\s+', content)) * 2
        score += len(re.findall(r'{%\s*with\s+', content)) * 1

        # Count includes and extends
        score += len(info.includes) * 2
        score += (1 if info.extends else 0) * 1

        # Count template tags
        score += len(re.findall(r'{%\s*\w+', content)) * 0.5

        # Penalize deep nesting (estimate by indentation)
        lines = content.split('\n')
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)
        score += (max_indent // 4) * 2  # Each 4-space indent adds complexity

        return int(score)

    def analyze_all(self):
        """Analyze all templates."""
        templates = self.find_templates()
        print(f"Found {len(templates)} templates\n")

        for template_path in templates:
            # Calculate relative name
            for template_dir in self.template_dirs:
                try:
                    rel_name = str(template_path.relative_to(template_dir))
                    break
                except ValueError:
                    continue
            else:
                rel_name = template_path.name

            info = self.analyze_template(template_path)
            self.templates[rel_name] = info

    def find_unused_templates(self) -> List[str]:
        """Find templates that are never referenced."""
        # Find referenced templates from views (simplified)
        # In a real implementation, this would scan views.py files

        unused = []
        for template_name, info in self.templates.items():
            # Skip if it's a base template (commonly extended)
            if 'base' in template_name.lower():
                continue

            # Check if referenced by other templates
            if template_name not in self.referenced_templates:
                # Check if it might be used directly by views
                # Templates in root or with common names are likely used
                if '/' not in template_name or 'index' in template_name or 'detail' in template_name:
                    continue

                unused.append(template_name)

        return sorted(unused)

    def check_inheritance_blocks(self) -> Dict[str, List[str]]:
        """Check for blocks defined in parent but not used in children."""
        issues = defaultdict(list)

        for template_name, info in self.templates.items():
            if not info.extends:
                continue

            # Find parent template
            parent_info = self.templates.get(info.extends)
            if not parent_info:
                issues[template_name].append(f"Parent template '{info.extends}' not found")
                continue

            # Check if child overrides any blocks
            if parent_info.blocks and not info.blocks:
                issues[template_name].append(
                    f"Child template does not override any blocks from parent "
                    f"(available: {', '.join(sorted(parent_info.blocks))})"
                )

        return dict(issues)

    def get_inheritance_chain(self, template_name: str) -> List[str]:
        """Get the inheritance chain for a template."""
        chain = [template_name]
        current = template_name

        visited = set()
        while current in self.templates:
            info = self.templates[current]
            if not info.extends:
                break

            # Prevent infinite loops
            if info.extends in visited:
                chain.append(f"{info.extends} (circular reference!)")
                break

            visited.add(current)
            chain.append(info.extends)
            current = info.extends

        return chain

    def check_performance_issues(self) -> Dict[str, List[str]]:
        """Check for performance issues."""
        issues = defaultdict(list)

        for template_name, info in self.templates.items():
            # Check for potential N+1 queries
            if info.queries_potential > 5:
                issues[template_name].append(
                    f"High query potential: {info.queries_potential} potential queries detected. "
                    f"Consider using select_related/prefetch_related in view."
                )

            # Check for missing caching in complex templates
            if info.complexity_score > 50 and info.cached_fragments == 0:
                issues[template_name].append(
                    f"Complex template (score: {info.complexity_score}) with no caching. "
                    f"Consider adding {{% cache %}} tags."
                )

            # Check for many includes without caching
            if len(info.includes) > 5 and info.cached_fragments == 0:
                issues[template_name].append(
                    f"Many includes ({len(info.includes)}) without caching. "
                    f"Consider caching expensive includes."
                )

        return dict(issues)

    def get_metrics(self) -> Dict[str, any]:
        """Get overall template metrics."""
        total_templates = len(self.templates)
        total_blocks = sum(len(info.blocks) for info in self.templates.values())
        total_includes = sum(len(info.includes) for info in self.templates.values())
        total_cached = sum(1 for info in self.templates.values() if info.cached_fragments > 0)

        avg_complexity = (
            sum(info.complexity_score for info in self.templates.values()) / total_templates
            if total_templates > 0 else 0
        )

        # Find most complex templates
        complex_templates = sorted(
            self.templates.items(),
            key=lambda x: x[1].complexity_score,
            reverse=True
        )[:5]

        return {
            'total_templates': total_templates,
            'total_blocks': total_blocks,
            'total_includes': total_includes,
            'cached_templates': total_cached,
            'avg_complexity': avg_complexity,
            'most_complex': [(name, info.complexity_score) for name, info in complex_templates],
        }


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Django templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'template_dirs',
        nargs='*',
        default=['templates'],
        help='Template directories to analyze (default: templates/)'
    )
    parser.add_argument(
        '--find-unused',
        action='store_true',
        help='Find unused templates'
    )
    parser.add_argument(
        '--check-blocks',
        action='store_true',
        help='Check for missing blocks in inheritance'
    )
    parser.add_argument(
        '--check-performance',
        action='store_true',
        help='Check for performance issues'
    )
    parser.add_argument(
        '--show-inheritance',
        metavar='TEMPLATE',
        help='Show inheritance chain for a template'
    )
    parser.add_argument(
        '--metrics',
        action='store_true',
        help='Show template metrics'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all checks'
    )

    args = parser.parse_args()

    # Convert template dirs to Path objects
    template_dirs = [Path(d) for d in args.template_dirs]

    # Create analyzer
    analyzer = TemplateAnalyzer(template_dirs)

    # Analyze all templates
    print("Analyzing templates...")
    analyzer.analyze_all()

    # Run requested analyses
    if args.all:
        args.find_unused = True
        args.check_blocks = True
        args.check_performance = True
        args.metrics = True

    if args.find_unused or args.all:
        print("\n" + "=" * 60)
        print("UNUSED TEMPLATES")
        print("=" * 60)
        unused = analyzer.find_unused_templates()
        if unused:
            for template in unused:
                print(f"  - {template}")
            print(f"\nTotal: {len(unused)} potentially unused templates")
        else:
            print("  No unused templates found")

    if args.check_blocks or args.all:
        print("\n" + "=" * 60)
        print("INHERITANCE ISSUES")
        print("=" * 60)
        issues = analyzer.check_inheritance_blocks()
        if issues:
            for template, problems in issues.items():
                print(f"\n{template}:")
                for problem in problems:
                    print(f"  - {problem}")
        else:
            print("  No inheritance issues found")

    if args.check_performance or args.all:
        print("\n" + "=" * 60)
        print("PERFORMANCE ISSUES")
        print("=" * 60)
        issues = analyzer.check_performance_issues()
        if issues:
            for template, problems in issues.items():
                print(f"\n{template}:")
                for problem in problems:
                    print(f"  - {problem}")
        else:
            print("  No performance issues detected")

    if args.show_inheritance:
        print("\n" + "=" * 60)
        print(f"INHERITANCE CHAIN: {args.show_inheritance}")
        print("=" * 60)
        chain = analyzer.get_inheritance_chain(args.show_inheritance)
        for i, template in enumerate(chain):
            indent = "  " * i
            arrow = "└─ " if i > 0 else ""
            print(f"{indent}{arrow}{template}")

            # Show blocks at each level
            if template in analyzer.templates:
                info = analyzer.templates[template]
                if info.blocks:
                    blocks_indent = "  " * (i + 1)
                    print(f"{blocks_indent}Blocks: {', '.join(sorted(info.blocks))}")

    if args.metrics or args.all:
        print("\n" + "=" * 60)
        print("TEMPLATE METRICS")
        print("=" * 60)
        metrics = analyzer.get_metrics()
        print(f"Total templates:      {metrics['total_templates']}")
        print(f"Total blocks:         {metrics['total_blocks']}")
        print(f"Total includes:       {metrics['total_includes']}")
        print(f"Cached templates:     {metrics['cached_templates']}")
        print(f"Average complexity:   {metrics['avg_complexity']:.1f}")
        print("\nMost complex templates:")
        for name, score in metrics['most_complex']:
            print(f"  {score:3d} - {name}")

    # If no specific action, show help
    if not any([args.find_unused, args.check_blocks, args.check_performance,
                args.show_inheritance, args.metrics, args.all]):
        parser.print_help()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
