"""
This module includes some utility functions for inspecting the layout
of a GDAL data source -- the functionality is analogous to the output
produced by the `ogrinfo` utility.
"""

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.geometries import GEO_CLASSES

def ogrinfo(data_source, num_features=10):
    """
    Walks the available layers in the supplied `data_source`, displaying
    the fields for the first `num_features` features.
    """

    # Checking the parameters.
    if isinstance(data_source, str):
        data_source = DataSource(data_source)
    elif isinstance(data_source, DataSource):
        pass
    else:
        raise Exception, 'Data source parameter must be a string or a DataSource object.'

    for i, layer in enumerate(data_source):
        print "data source : %s" % data_source.name
        print "==== layer %s" % i
        print "  shape type: %s" % GEO_CLASSES[layer.geom_type.num].__name__
        print "  # features: %s" % len(layer)
        print "         srs: %s" % layer.srs
        extent_tup = layer.extent.tuple
        print "      extent: %s - %s" % (extent_tup[0:2], extent_tup[2:4])
        print "Displaying the first %s features ====" % num_features

        width = max(*map(len,layer.fields))
        fmt = " %%%ss: %%s" % width
        for j, feature in enumerate(layer[:num_features]):
            print "=== Feature %s" % j
            for fld_name in layer.fields:
                type_name = feature[fld_name].type_name
                output = fmt % (fld_name, type_name)
                val = feature.get(fld_name)
                if val:
                    if isinstance(val, str):
                        val_fmt = ' ("%s")'
                    else:
                        val_fmt = ' (%s)'
                    output += val_fmt % val
                else:
                    output += ' (None)'
                print output

# For backwards compatibility.
sample = ogrinfo
