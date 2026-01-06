#!/usr/bin/env python
"""
Generate Django template tag boilerplate.

Usage:
    python generate_templatetag.py <app_name> <tag_name> --type [simple|inclusion|block]

Examples:
    python generate_templatetag.py blog post_tags --type simple
    python generate_templatetag.py core utils --type inclusion
    python generate_templatetag.py shop product_tags --type block
"""

import argparse
import sys
from pathlib import Path


SIMPLE_TAG_TEMPLATE = '''from django import template

register = template.Library()


@register.simple_tag
def {tag_name}(*args, **kwargs):
    """
    {description}

    Usage:
        {{% {tag_name} arg1 arg2 %}}
        {{% {tag_name} arg1 arg2 as result %}}
    """
    # TODO: Implement tag logic
    return ''


@register.simple_tag(takes_context=True)
def {tag_name}_with_context(context, *args, **kwargs):
    """
    {description} (with context access)

    Usage:
        {{% {tag_name}_with_context arg1 arg2 %}}
    """
    request = context.get('request')
    user = context.get('user')

    # TODO: Implement tag logic
    return ''
'''


INCLUSION_TAG_TEMPLATE = '''from django import template

register = template.Library()


@register.inclusion_tag('{app_name}/{tag_name}.html')
def {tag_name}(*args, **kwargs):
    """
    {description}

    Template: {app_name}/{tag_name}.html

    Usage:
        {{% {tag_name} arg1 arg2 %}}
    """
    # TODO: Implement tag logic and return context dict
    return {{
        'data': None,
    }}


@register.inclusion_tag('{app_name}/{tag_name}_context.html', takes_context=True)
def {tag_name}_with_context(context, *args, **kwargs):
    """
    {description} (with context access)

    Template: {app_name}/{tag_name}_context.html

    Usage:
        {{% {tag_name}_with_context arg1 arg2 %}}
    """
    request = context.get('request')

    # TODO: Implement tag logic and return context dict
    return {{
        'request': request,
        'data': None,
    }}
'''


INCLUSION_TAG_HTML_TEMPLATE = '''<div class="{tag_name}">
    <!-- TODO: Implement template markup -->
    {{ data }}
</div>
'''


BLOCK_TAG_TEMPLATE = '''from django import template
from django.template.base import Node, NodeList

register = template.Library()


class {tag_class_name}Node(Node):
    """Node class for {tag_name} block tag."""

    def __init__(self, nodelist, *args):
        self.nodelist = nodelist
        # TODO: Store parsed arguments
        # self.arg1 = template.Variable(arg1)

    def render(self, context):
        """Render the block tag."""
        # TODO: Resolve variables from context
        # arg1_value = self.arg1.resolve(context)

        # Render enclosed content
        output = self.nodelist.render(context)

        # TODO: Process output as needed
        return output


@register.tag
def {tag_name}(parser, token):
    """
    {description}

    Usage:
        {{% {tag_name} arg1 arg2 %}}
            Content to process
        {{% end{tag_name} %}}
    """
    try:
        # Parse tag arguments
        bits = token.split_contents()
        tag_name = bits[0]
        # TODO: Extract and validate arguments
        # if len(bits) < 2:
        #     raise template.TemplateSyntaxError(
        #         f"{{tag_name}} tag requires at least one argument"
        #     )

    except ValueError as e:
        raise template.TemplateSyntaxError(
            f"{{tag_name}} tag error: {{str(e)}}"
        )

    # Parse content until closing tag
    nodelist = parser.parse((f'end{{tag_name}}',))
    parser.delete_first_token()

    # Return node instance
    return {tag_class_name}Node(nodelist)


class Conditional{tag_class_name}Node(Node):
    """Node class for {tag_name}_if block tag with conditional rendering."""

    def __init__(self, condition, nodelist_true, nodelist_false):
        self.condition = template.Variable(condition)
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        """Render based on condition."""
        try:
            condition_value = self.condition.resolve(context)

            if condition_value:
                return self.nodelist_true.render(context)
            else:
                return self.nodelist_false.render(context)
        except template.VariableDoesNotExist:
            return self.nodelist_false.render(context)


@register.tag
def {tag_name}_if(parser, token):
    """
    Conditional {tag_name} block tag.

    Usage:
        {{% {tag_name}_if condition %}}
            Content if true
        {{% else %}}
            Content if false
        {{% end{tag_name}_if %}}
    """
    try:
        bits = token.split_contents()
        if len(bits) != 2:
            raise template.TemplateSyntaxError(
                f"{{{tag_name}_if}} tag requires exactly one argument"
            )

        tag_name = bits[0]
        condition = bits[1]

    except ValueError as e:
        raise template.TemplateSyntaxError(str(e))

    # Parse true branch
    nodelist_true = parser.parse(('else', f'end{{{tag_name}_if}}'))
    token = parser.next_token()

    # Parse false branch if else present
    if token.contents == 'else':
        nodelist_false = parser.parse((f'end{{{tag_name}_if}}',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()

    return Conditional{tag_class_name}Node(condition, nodelist_true, nodelist_false)
'''


def to_class_name(tag_name):
    """Convert tag_name to PascalCase class name."""
    return ''.join(word.capitalize() for word in tag_name.split('_'))


def generate_simple_tag(app_name, tag_name, library_name, description):
    """Generate simple tag boilerplate."""
    return SIMPLE_TAG_TEMPLATE.format(
        tag_name=tag_name,
        description=description,
    )


def generate_inclusion_tag(app_name, tag_name, library_name, description):
    """Generate inclusion tag boilerplate and template."""
    code = INCLUSION_TAG_TEMPLATE.format(
        app_name=app_name,
        tag_name=tag_name,
        description=description,
    )

    html = INCLUSION_TAG_HTML_TEMPLATE.format(
        tag_name=tag_name,
    )

    return code, html


def generate_block_tag(app_name, tag_name, library_name, description):
    """Generate block tag boilerplate."""
    tag_class_name = to_class_name(tag_name)

    return BLOCK_TAG_TEMPLATE.format(
        tag_name=tag_name,
        tag_class_name=tag_class_name,
        description=description,
    )


def find_django_app(app_name):
    """Find Django app directory."""
    # Try current directory first
    app_path = Path.cwd() / app_name
    if app_path.exists() and app_path.is_dir():
        return app_path

    # Try parent directory
    app_path = Path.cwd().parent / app_name
    if app_path.exists() and app_path.is_dir():
        return app_path

    # Try common project structures
    for parent in ['apps', 'src', '.']:
        app_path = Path.cwd() / parent / app_name
        if app_path.exists() and app_path.is_dir():
            return app_path

    return None


def main():
    parser = argparse.ArgumentParser(
        description='Generate Django template tag boilerplate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('app_name', help='Django app name')
    parser.add_argument('library_name', help='Template tag library name (e.g., blog_tags)')
    parser.add_argument(
        '--type',
        choices=['simple', 'inclusion', 'block'],
        default='simple',
        help='Type of template tag (default: simple)'
    )
    parser.add_argument(
        '--tag-name',
        help='Specific tag name (default: derived from library name)'
    )
    parser.add_argument(
        '--description',
        default='TODO: Add description',
        help='Tag description'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files'
    )

    args = parser.parse_args()

    # Find app directory
    app_path = find_django_app(args.app_name)
    if not app_path:
        print(f"Error: Django app '{args.app_name}' not found", file=sys.stderr)
        print(f"Searched in: {Path.cwd()}, parent, apps/, src/", file=sys.stderr)
        return 1

    # Determine tag name
    tag_name = args.tag_name or args.library_name.replace('_tags', '')

    # Create templatetags directory
    templatetags_dir = app_path / 'templatetags'
    templatetags_dir.mkdir(exist_ok=True)

    # Create __init__.py if it doesn't exist
    init_file = templatetags_dir / '__init__.py'
    if not init_file.exists():
        init_file.touch()
        print(f"Created: {init_file}")

    # Create library file
    library_file = templatetags_dir / f'{args.library_name}.py'

    if library_file.exists() and not args.force:
        print(f"Error: {library_file} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1

    # Generate code based on type
    if args.type == 'simple':
        code = generate_simple_tag(args.app_name, tag_name, args.library_name, args.description)
        library_file.write_text(code)
        print(f"Created: {library_file}")

    elif args.type == 'inclusion':
        code, html = generate_inclusion_tag(args.app_name, tag_name, args.library_name, args.description)
        library_file.write_text(code)
        print(f"Created: {library_file}")

        # Create template directory and file
        templates_dir = app_path / 'templates' / args.app_name
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_file = templates_dir / f'{tag_name}.html'
        if not template_file.exists() or args.force:
            template_file.write_text(html)
            print(f"Created: {template_file}")

        template_file_context = templates_dir / f'{tag_name}_context.html'
        if not template_file_context.exists() or args.force:
            template_file_context.write_text(html)
            print(f"Created: {template_file_context}")

    elif args.type == 'block':
        code = generate_block_tag(args.app_name, tag_name, args.library_name, args.description)
        library_file.write_text(code)
        print(f"Created: {library_file}")

    # Print usage instructions
    print("\n" + "=" * 60)
    print("Template tag generated successfully!")
    print("=" * 60)
    print(f"\nTag type: {args.type}")
    print(f"Library: {args.library_name}")
    print(f"Tag name: {tag_name}")
    print("\nUsage in templates:")
    print(f"  {{% load {args.library_name} %}}")

    if args.type == 'simple':
        print(f"  {{% {tag_name} arg1 arg2 %}}")
        print(f"  {{% {tag_name} arg1 arg2 as result %}}")
    elif args.type == 'inclusion':
        print(f"  {{% {tag_name} arg1 arg2 %}}")
    elif args.type == 'block':
        print(f"  {{% {tag_name} arg1 arg2 %}}")
        print(f"    Content")
        print(f"  {{% end{tag_name} %}}")

    print("\nNext steps:")
    print("  1. Implement the tag logic in the generated file")
    print("  2. Add the tag library to your template with {% load " + args.library_name + " %}")
    print("  3. Test the tag in your templates")

    return 0


if __name__ == '__main__':
    sys.exit(main())
