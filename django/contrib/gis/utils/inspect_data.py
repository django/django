"""
This module includes some utility functions for inspecting the layout
of a gdal.DataSource.
"""

from django.contrib.gis.gdal.OGRGeometry import GEO_CLASSES

def sample(data_source, num_features=10, gcs_file=None):
    """
    Walks the available layers in the supplied ``data_source``, displaying
    the fields for the first ``num_features`` features.
    """

    for i, layer in enumerate(data_source):
        print "data source : %s" % data_source.name
        print "==== layer %s" % i
        print "  shape type: %s" % GEO_CLASSES[layer.geom_type.num].__name__
        print "  # features: %s" % len(layer)
        print "         srs: %s" % layer.srs
        print "Showing first %s features ========" % num_features

        width = max(*map(len,layer.fields))
        fmt = " %%%ss:%%s" % width
        for i, feature in enumerate(layer[:num_features]):
            print "======== Feature %s" % i
            for field in layer.fields:
                print fmt % (field, feature.get(field))
