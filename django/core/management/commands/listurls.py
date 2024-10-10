import re
from importlib import import_module
from io import StringIO

from django.contrib.admindocs.views import (
    extract_views_from_urlpatterns,
    simplify_regex,
)
from django.core.management.base import BaseCommand


def replace_simple_regex(value, offset):
    if value == "<var>":
        return "<arg:{}>".format(offset)
    else:
        just_value = value.strip("<").strip(">")
        return "<kwarg:{}>".format(just_value)


class Command(BaseCommand):
    help = """Displays a list of urls used in the project."""

    def add_arguments(self, parser):
        parser.add_argument(
            "url_prefix",
            nargs="*",
            help="Only list URLs with these URL prefixes.",
        )

        parser.add_argument(
            "--table",
            action="store_true",
            help="Display the URLs in a table.",
        )

    def handle(self, *args, **options):
        table = options["table"]

        output = StringIO()

        for url in self.urls(options.get("url_prefix")):
            output.write("\n")
            if table:
                output.write(self.table_url(url))
            else:
                output.write(self.multiline_url(url))

        out_text = output.getvalue()
        if len(out_text.strip()) <= 0:
            return "There are no URLs that match those prefixes"
        return out_text

    def table_url(self, url):
        simple_url = url[1]
        path = self.style.HTTP_REDIRECT(simple_url)

        view_func = getattr(url[0], "__name__", url[0].__class__.__name__)
        view_module = url[0]
        view_method = f"{view_module}.{view_func}"

        name = self.view_name(url)
        name = name if name else ""

        return f"{path}\t{view_method}\t{name}"

    def multiline_url(self, url):
        simple_url = url[1]
        uri = "URL: " + self.style.HTTP_REDIRECT(simple_url)

        viewfunc = url[0]
        viewname = "{}.{}".format(
            viewfunc.__module__,
            getattr(viewfunc, "__name__", viewfunc.__class__.__name__),
        )
        view = "View: " + self.style.HTTP_NOT_MODIFIED(viewname)

        name = self.view_name(url)
        if name:
            name = "Name: " + self.style.HTTP_INFO(name)

        arguments = None
        named_groups = re.compile(r"<\w+>").findall(simple_url)
        all_groups = (
            replace_simple_regex(var, index)
            for index, var in enumerate(named_groups, start=1)
        )
        if all_groups:
            arguments = "Arguments: " + self.style.HTTP_INFO(
                ", ".join(tuple(all_groups))
            )
        linelength = "-" * 20

        lineparts = (uri, view, name, arguments, linelength + "\n")
        return "\n".join(part for part in lineparts if part is not None)

    def view_name(self, url):
        try:
            namespace_list = url[2]
        except IndexError:
            namespace_list = []

        try:
            name = url[3]
        except IndexError:
            name = None

        namespace = ""
        if namespace_list:
            for part in namespace_list:
                namespace += part + ":"

        return namespace + name if name else None

    def urls(self, url_prefixes=None):
        from django.conf import settings

        urlconf = import_module(settings.ROOT_URLCONF)
        all_urls = extract_views_from_urlpatterns(urlconf.urlpatterns)

        url_prefixes = url_prefixes or []

        if isinstance(url_prefixes, str):
            url_prefixes = [url_prefixes]

        url_prefixes = [f"/{u}" if not u.startswith("/") else u for u in url_prefixes]

        for url in all_urls:
            simple_url = simplify_regex(url[1])
            if not url_prefixes:
                yield url
                continue

            if any(u == simple_url[: len(u)] for u in url_prefixes):
                yield url
