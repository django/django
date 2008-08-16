from django.contrib.syndication.feeds import Feed as BaseFeed, FeedDoesNotExist
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

class GeoFeedMixin(object):
    """
    This mixin provides the necessary routines for SyndicationFeed subclasses
    to produce simple GeoRSS or W3C Geo elements.
    """

    def georss_coords(self, coords):
        """
        In GeoRSS coordinate pairs are ordered by lat/lon and separated by
        a single white space.  Given a tuple of coordinates, this will return
        a unicode GeoRSS representation.
        """
        return u' '.join([u'%f %f' % (coord[1], coord[0]) for coord in coords])

    def add_georss_point(self, handler, coords, w3c_geo=False):
        """
        Adds a GeoRSS point with the given coords using the given handler.
        Handles the differences between simple GeoRSS and the more pouplar
        W3C Geo specification.
        """
        if w3c_geo:
            lon, lat = coords[:2]
            handler.addQuickElement(u'geo:lat', u'%f' % lat)
            handler.addQuickElement(u'geo:lon', u'%f' % lon)
        else:
            handler.addQuickElement(u'georss:point', self.georss_coords((coords,)))

    def add_georss_element(self, handler, item, w3c_geo=False):
        """
        This routine adds a GeoRSS XML element using the given item and handler.
        """
        # Getting the Geometry object.
        geom = item.get('geometry', None)
        if not geom is None:
            if isinstance(geom, (list, tuple)):
                # Special case if a tuple/list was passed in.  The tuple may be
                # a point or a box
                box_coords = None
                if isinstance(geom[0], (list, tuple)):
                    # Box: ( (X0, Y0), (X1, Y1) )
                    if len(geom) == 2:
                        box_coords = geom
                    else:
                        raise ValueError('Only should be two sets of coordinates.')
                else:
                    if len(geom) == 2:
                        # Point: (X, Y)
                        self.add_georss_point(handler, geom, w3c_geo=w3c_geo)
                    elif len(geom) == 4:
                        # Box: (X0, Y0, X1, Y1)
                        box_coords = (geom[:2], geom[2:])
                    else:
                        raise ValueError('Only should be 2 or 4 numeric elements.')
                # If a GeoRSS box was given via tuple.
                if not box_coords is None:
                    if w3c_geo: raise ValueError('Cannot use simple GeoRSS box in W3C Geo feeds.')
                    handler.addQuickElement(u'georss:box', self.georss_coords(box_coords))
            else:
                # Getting the lower-case geometry type.
                gtype = str(geom.geom_type).lower()
                if gtype == 'point':
                    self.add_georss_point(handler, geom.coords, w3c_geo=w3c_geo) 
                else:
                    if w3c_geo: raise ValueError('W3C Geo only supports Point geometries.')
                    # For formatting consistent w/the GeoRSS simple standard:
                    # http://georss.org/1.0#simple
                    if gtype in ('linestring', 'linearring'):
                        handler.addQuickElement(u'georss:line', self.georss_coords(geom.coords))
                    elif gtype in ('polygon',):
                        # Only support the exterior ring.
                        handler.addQuickElement(u'georss:polygon', self.georss_coords(geom[0].coords))
                    else:
                        raise ValueError('Geometry type "%s" not supported.' % geom.geom_type)

### SyndicationFeed subclasses ###
class GeoRSSFeed(Rss201rev2Feed, GeoFeedMixin):
    def rss_attributes(self):
        attrs = super(GeoRSSFeed, self).rss_attributes()
        attrs[u'xmlns:georss'] = u'http://www.georss.org/georss'
        return attrs

    def add_item_elements(self, handler, item):
        super(GeoRSSFeed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item)

    def add_root_elements(self, handler):
        super(GeoRSSFeed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed)

class GeoAtom1Feed(Atom1Feed, GeoFeedMixin):
    def root_attributes(self):
        attrs = super(GeoAtom1Feed, self).root_attributes()
        attrs[u'xmlns:georss'] = u'http://www.georss.org/georss'
        return attrs

    def add_item_elements(self, handler, item):
        super(GeoAtom1Feed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item)

    def add_root_elements(self, handler):
        super(GeoAtom1Feed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed)

class W3CGeoFeed(Rss201rev2Feed, GeoFeedMixin):
    def rss_attributes(self):
        attrs = super(W3CGeoFeed, self).rss_attributes()
        attrs[u'xmlns:geo'] = u'http://www.w3.org/2003/01/geo/wgs84_pos#'
        return attrs

    def add_item_elements(self, handler, item):
        super(W3CGeoFeed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item, w3c_geo=True)

    def add_root_elements(self, handler):
        super(W3CGeoFeed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed, w3c_geo=True)

### Feed subclass ###
class Feed(BaseFeed):
    """
    This is a subclass of the `Feed` from `django.contrib.syndication`.
    This allows users to define a `geometry(obj)` and/or `item_geometry(item)`
    methods on their own subclasses so that geo-referenced information may
    placed in the feed.
    """
    feed_type = GeoRSSFeed

    def feed_extra_kwargs(self, obj):
        return {'geometry' : self.__get_dynamic_attr('geometry', obj)}

    def item_extra_kwargs(self, item):
        return {'geometry' : self.__get_dynamic_attr('item_geometry', item)}
