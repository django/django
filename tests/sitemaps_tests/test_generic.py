from datetime import datetime
import logging
import random
import time

from django.contrib.sitemaps import GenericSitemap, Sitemap
from django.test import override_settings
from django.conf import settings
from django.core.cache import cache

from .base import SitemapTestsBase
from .models import TestModel


logging.basicConfig(level=logging.INFO, format='%(message)s')


@override_settings(ABSOLUTE_URL_OVERRIDES={})
class GenericViewsSitemapTests(SitemapTestsBase):
    def test_generic_sitemap_attributes(self):
        datetime_value = datetime.now()
        queryset = TestModel.objects.all()
        generic_sitemap = GenericSitemap(
            info_dict={
                "queryset": queryset,
                "date_field": datetime_value,
            },
            priority=0.6,
            changefreq="monthly",
            protocol="https",
        )
        attr_values = (
            ("date_field", datetime_value),
            ("priority", 0.6),
            ("changefreq", "monthly"),
            ("protocol", "https"),
        )
        for attr_name, expected_value in attr_values:
            with self.subTest(attr_name=attr_name):
                self.assertEqual(getattr(generic_sitemap, attr_name), expected_value)
        self.assertCountEqual(generic_sitemap.queryset, queryset)

    def test_generic_sitemap(self):
        "A minimal generic sitemap can be rendered"
        response = self.client.get("/generic/sitemap.xml")
        expected = ""
        for pk in TestModel.objects.values_list("id", flat=True):
            expected += "<url><loc>%s/testmodel/%s/</loc></url>" % (self.base_url, pk)
        expected_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            "%s\n"
            "</urlset>"
        ) % expected
        self.assertXMLEqual(response.text, expected_content)

    def test_generic_sitemap_lastmod(self):
        test_model = TestModel.objects.first()
        TestModel.objects.update(lastmod=datetime(2013, 3, 13, 10, 0, 0))
        response = self.client.get("/generic-lastmod/sitemap.xml")
        expected_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            "<url><loc>%s/testmodel/%s/</loc><lastmod>2013-03-13</lastmod></url>\n"
            "</urlset>"
        ) % (
            self.base_url,
            test_model.pk,
        )
        self.assertXMLEqual(response.text, expected_content)
        self.assertEqual(
            response.headers["Last-Modified"], "Wed, 13 Mar 2013 10:00:00 GMT"
        )

    def test_get_protocol_defined_in_constructor(self):
        for protocol in ["http", "https"]:
            with self.subTest(protocol=protocol):
                sitemap = GenericSitemap({"queryset": None}, protocol=protocol)
                self.assertEqual(sitemap.get_protocol(), protocol)

    def test_get_protocol_passed_as_argument(self):
        sitemap = GenericSitemap({"queryset": None})
        for protocol in ["http", "https"]:
            with self.subTest(protocol=protocol):
                self.assertEqual(sitemap.get_protocol(protocol), protocol)

    def test_get_protocol_default(self):
        sitemap = GenericSitemap({"queryset": None})
        self.assertEqual(sitemap.get_protocol(), "https")

    def test_generic_sitemap_index(self):
        TestModel.objects.update(lastmod=datetime(2013, 3, 13, 10, 0, 0))
        response = self.client.get("/generic-lastmod/index.xml")
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>http://example.com/simple/sitemap-generic.xml</loc><lastmod>2013-03-13T10:00:00</lastmod></sitemap>
</sitemapindex>"""
        self.assertXMLEqual(response.text, expected_content)

    def test_items_sitemap_cache(self):
        sitemap = Sitemap()
        large_items_list = [
            f"item_{random.randint(1, 2000000)}" for _ in range(2000000)
        ]
        sitemap._cached_items = large_items_list
        start = time.perf_counter()
        result1 = sitemap.items()
        time1 = time.perf_counter() - start
        start = time.perf_counter()
        result2 = sitemap.items()
        time2 = time.perf_counter() - start
        self.assertEqual(len(result1), 2000000)
        self.assertIs(result1, result2, "Should return same cached object")
        logging.info(f"First call: {time1:.6f} seconds")
        logging.info(f"Cached call: {time2:.6f} seconds")
        logging.info(f"✓ Cache hit: {time2 < time1}")

    def test_languages_sitemap_cache(self):
        sitemap = Sitemap()
        sitemap.languages = None
        start = time.perf_counter()
        langs1 = sitemap._languages
        time1 = time.perf_counter() - start
        logging.info(f"First access loaded {len(langs1)} language codes in {time1:.6f}s")
        logging.info(f"Language codes: {langs1}")
        start = time.perf_counter()
        langs2 = sitemap._languages
        time2 = time.perf_counter() - start
        self.assertIs(langs1, langs2, "Cache failed: objects are different!")
        self.assertLess(
            time2, time1,
            f"Cache not faster! First: {time1:.6f}s, Cached {time2:.6f}"
        )
        logging.info(f"Cached access took {time2:.6f}s")
        logging.info(f"Cache hit: {langs1 is langs2}")
        logging.info(f"Cache is {time1/time2:.1f}x faster")

    def test_queryset_before_pagination(self):
        ...
