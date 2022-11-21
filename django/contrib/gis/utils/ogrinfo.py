"""
This module includes some utility functions for inspecting the layout
of a GDAL data source -- the functionality is analogous to the output
produced by the `ogrinfo` utility.
"""

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.geometries import GEO_CLASSES


def ogrinfo(data_source, num_features=10):
    """
    Walk the available layers in the supplied `data_source`, displaying
    the fields for the first `num_features` features.
    """

    # Checking the parameters.
    if isinstance(data_source, str):
        data_source = DataSource(data_source)
    elif not isinstance(data_source, DataSource):
        raise Exception(
            "Data source parameter must be a string or a DataSource object."
        )

    for i, layer in enumerate(data_source):
        print(f"data source : {data_source.name}")
        print(f"==== layer {i}")
        print(f"  shape type: {GEO_CLASSES[layer.geom_type.num].__name__}")
        print(f"  # features: {len(layer)}")
        print(f"         srs: {layer.srs}")
        extent_tup = layer.extent.tuple
        print(f"      extent: {extent_tup[:2]} - {extent_tup[2:4]}")
        print(f"Displaying the first {num_features} features ====")

        width = max(*map(len, layer.fields))
        fmt = " %%%ss: %%s" % width
        for j, feature in enumerate(layer[:num_features]):
            print(f"=== Feature {j}")
            for fld_name in layer.fields:
                type_name = feature[fld_name].type_name
                output = fmt % (fld_name, type_name)
                if val := feature.get(fld_name):
                    val_fmt = ' ("%s")' if isinstance(val, str) else " (%s)"
                    output += val_fmt % val
                else:
                    output += " (None)"
                print(output)
