from django.contrib.sitemaps import ping_google
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ping Google with an updated sitemap, pass optional url of sitemap"

    def add_arguments(self, parser):
        parser.add_argument('sitemap_url', nargs='?')
        parser.add_argument('--sitemap-uses-http', action='store_true')

    def handle(self, *args, **options):
        ping_google(
            sitemap_url=options['sitemap_url'],
            sitemap_uses_https=not options['sitemap_uses_http'],
        )
