from django.core.management.base import BaseCommand
from django.contrib.sitemaps import ping_google


class Command(BaseCommand):
    help = "Ping Google with an updated sitemap, pass optional url of sitemap"

    def add_arguments(self, parser):
        parser.add_argument('sitemap_url', nargs='?', default=None)
        parser.add_argument('site_domain', nargs='?', default=None)
        parser.add_argument('is_secure', narg='?', default=False)

    def handle(self, *args, **options):
        ping_google(sitemap_url=options['sitemap_url'], site_domain=options['site_domain'],
                    is_secure=options['is_secure'])
