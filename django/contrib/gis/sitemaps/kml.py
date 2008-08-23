from django.core import urlresolvers
from django.contrib.sitemaps import Sitemap
from django.contrib.gis.db.models.fields import GeometryField
from django.db import models

class KMLSitemap(Sitemap):
    """
    A minimal hook to produce KML sitemaps.
    """
    geo_format = 'kml'

    def __init__(self, locations=None):
        # If no locations specified, then we try to build for
        # every model in installed applications.
        self.locations = self._build_kml_sources(locations)
        
    def _build_kml_sources(self, sources):
        """
        Goes through the given sources and returns a 3-tuple of
        the application label, module name, and field name of every
        GeometryField encountered in the sources.

        If no sources are provided, then all models.
        """
        kml_sources = []
        if sources is None:
            sources = models.get_models()
        for source in sources:
            if isinstance(source, models.base.ModelBase):
                for field in source._meta.fields:
                    if isinstance(field, GeometryField):
                        kml_sources.append((source._meta.app_label,
                                            source._meta.module_name,
                                            field.name))
            elif isinstance(source, (list, tuple)):
                if len(source) != 3: 
                    raise ValueError('Must specify a 3-tuple of (app_label, module_name, field_name).')
                kml_sources.append(source)
            else:
                raise TypeError('KML Sources must be a model or a 3-tuple.')
        return kml_sources

    def get_urls(self, page=1):
        """
        This method is overrridden so the appropriate `geo_format` attribute
        is placed on each URL element.
        """
        urls = Sitemap.get_urls(self, page=page)
        for url in urls: url['geo_format'] = self.geo_format
        return urls

    def items(self):
        return self.locations

    def location(self, obj):
        return urlresolvers.reverse('django.contrib.gis.sitemaps.views.%s' % self.geo_format,
                                    kwargs={'label' : obj[0], 
                                            'model' : obj[1],
                                            'field_name': obj[2],
                                            }
                                    )
class KMZSitemap(KMLSitemap):
    geo_format = 'kmz'
