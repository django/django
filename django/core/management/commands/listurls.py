# Portions of this code are derived from django-extensions (MIT):
# https://github.com/django-extensions/django-extensions

import json
from collections import namedtuple
from importlib import import_module

from django.conf import settings
from django.core.management import color
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.urls.utils import (
    extract_views_from_urlpatterns,
    simplify_regex,
)

FORMATS = (
    "tabular",
    "stacked",
    "json",
)

COLORLESS_FORMATS = ("json",)

URLPattern = namedtuple("URLPattern", ["route", "view", "name"])


class Command(BaseCommand):
    help = "List URL patterns in the project with optional filtering by prefixes."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.style = color.color_style()

    def add_arguments(self, parser: CommandParser):
        super().add_arguments(parser)

        parser.add_argument(
            "--unsorted",
            "-u",
            action="store_true",
            dest="unsorted",
            help="Show URLs without sorting them alphabetically.",
        )
        parser.add_argument(
            "--prefix",
            "-p",
            dest="prefixes",
            help="Only list URLs with these prefixes.",
            nargs="+",
        )
        parser.add_argument(
            "--format",
            "-f",
            choices=FORMATS,
            default="tabular",
            dest="format",
            help="Formatting style of the output",
        )

    def handle(self, *args, **options):
        prefixes = options["prefixes"]
        url_patterns = self.get_url_patterns(prefixes=prefixes)
        if not url_patterns:
            raise CommandError("There are no URL patterns that match given prefixes")

        unsorted = options["unsorted"]
        no_color = options["no_color"]
        format = options["format"]
        if not unsorted:
            url_patterns.sort()

        self.is_color_enabled = (
            color.supports_color()
            and (not no_color)
            and (format not in COLORLESS_FORMATS)
        )
        if self.is_color_enabled:
            url_patterns = self.apply_color(url_patterns=url_patterns)

        url_patterns = self.apply_format(url_patterns=url_patterns, format=format)
        return url_patterns

    @classmethod
    def get_url_patterns(cls, prefixes=None):
        """
        Returns a list of URL patterns in the project with given prefixes.

        Each object in the returned list is a tuple[str, str, str]:
        (route, view, name).
        """
        url_patterns = []
        urlconf = import_module(settings.ROOT_URLCONF)

        for view_func, regex, namespace, name in extract_views_from_urlpatterns(
            urlconf.urlpatterns
        ):
            route = simplify_regex(regex)

            if hasattr(view_func, "view_class"):
                view_func = view_func.view_class

            view = "{}.{}".format(
                view_func.__module__,
                getattr(view_func, "__name__", view_func.__class__.__name__),
            )
            namespace_list = namespace or []
            name = ":".join(namespace_list + [name]) if name else ""

            pattern = URLPattern(route, view, name)
            if not prefixes or any(
                pattern.route.startswith(prefix) for prefix in prefixes
            ):
                url_patterns.append(pattern)

        return url_patterns

    def apply_color(self, url_patterns):
        colored_url_patterns = []

        for url_pattern in url_patterns:
            route = self.style.COMMAND_DATA(url_pattern.route)

            module_path, module_name = url_pattern.view.rsplit(".", 1)
            module_name = self.style.COMMAND_HIGHLIGHT(module_name)
            view = f"{module_path}.{module_name}"

            if name := url_pattern.name:
                namespace, name = name.rsplit(":", 1) if ":" in name else ("", name)
                name = self.style.COMMAND_HIGHLIGHT(name)
                name = f"{namespace}:{name}" if namespace else name

            colored_url_patterns.append((route, view, name))

        return colored_url_patterns

    def apply_format(self, url_patterns, format):
        format_method_name = f"format_{format.replace('-', '_')}"
        format_method = getattr(self, format_method_name)
        return format_method(url_patterns)

    def format_tabular(self, url_patterns):
        widths = []
        margin = 2
        for columns in zip(*url_patterns, strict=False):
            widths.append(len(max(columns, key=len)) + margin)

        lines = []
        for row in url_patterns:
            line = "".join(
                cdata.ljust(width) for width, cdata in zip(widths, row, strict=False)
            )
            lines.append(line)

        return "\n".join(lines)

    def format_stacked(self, url_patterns):
        separator = "-" * 20
        apply_style = (
            self.style.COMMAND_HEADER if self.is_color_enabled else lambda text: text
        )

        lines = []
        for route, view, name in url_patterns:
            lines.append(apply_style("Route: ") + route)
            lines.append(apply_style("View: ") + view)
            if name:
                lines.append(apply_style("Name: ") + name)
            lines.append(separator)

        return "\n".join(lines)

    def format_json(self, url_patterns):
        url_pattern_dicts = [url_pattern._asdict() for url_pattern in url_patterns]
        return json.dumps(url_pattern_dicts, indent=2)
