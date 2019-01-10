from django.contrib.sitemaps import ping_google
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ping Google with an updated sitemap, pass optional url of sitemap"

    def add_arguments(self, parser):
        parser.add_argument('sitemap_url', nargs='?')
        parser.add_argument('-d', '--site-domain')
        parser.add_argument('--use-http', default=False, action='store_false')

    def handle(self, *args, **options):
        ping_google(
            sitemap_url=options['sitemap_url'],
            site_domain=options['site_domain'],
            use_http=options['use_http'],
        )
