"""
 This module is for inspecting OGR data sources and generating either
 models for GeoDjango and/or mapping dictionaries for use with the
 LayerMapping utility.

 Author: Travis Pinney
"""

# Requires GDAL to use.
from django.contrib.gis.gdal import DataSource

def mapping(data_source, geom_name='geom', layer_key=0):
    """
    Given a DataSource, generates a dictionary that may be used 
    for invoking the LayerMapping utility.

    Keyword Arguments:
     `geom_name` => The name of the geometry field to use for the model.

     `layer_key` => The key for specifying which layer in the DataSource to use;
       defaults to 0 (the first layer).  May be an integer index or a string
       identifier for the layer.
    """
    if isinstance(data_source, basestring):
        # Instantiating the DataSource from the string.
        data_source = DataSource(data_source)
    elif isinstance(data_source, DataSource):
        pass
    else:
        raise TypeError('Data source parameter must be a string or a DataSource object.')
    
    # Creating the dictionary.
    _mapping = {}

    # Generating the field name for each field in the layer.
    for field in data_source[layer_key].fields:
        mfield = field.lower()
        if mfield[-1:] == '_': mfield += 'field'
        _mapping[mfield] = field
    gtype = data_source[layer_key].geom_type
    _mapping[geom_name] = str(gtype).upper()

    return _mapping

def ogrinspect(*args, **kwargs):
    """
    Given a data source (either a string or a DataSource object) and a string
    model name this function will generate a GeoDjango model.

    Keyword Arguments
     `geom_name` => For specifying the model name for the Geometry Field.

     `layer_key` => The key for specifying which layer in the DataSource to use;
       defaults to 0 (the first layer).  May be an integer index or a string
       identifier for the layer.

     `srid` => The SRID to use for the Geometry Field.  If it can be determined,
       the SRID of the datasource

    Note: This routine calls the _ogrinspect() helper to do the heavy lifting.
    """
    return '\n'.join(s for s in _ogrinspect(*args, **kwargs))

def _ogrinspect(data_source, model_name, geom_name='geom', layer_key=0, srid=None):
    """
    Helper routine for `ogrinspect` that generates GeoDjango models corresponding
    to the given data source.  See the `ogrinspect` docstring for more details.
    """

    # Getting the DataSource
    if isinstance(data_source, str):
        data_source = DataSource(data_source)
    elif isinstance(data_source, DataSource):
        pass
    else:
        raise TypeError('Data source parameter must be a string or a DataSource object.')

    yield '# This is an auto-generated Django model module created by ogrinspect.'
    yield 'from django.contrib.gis.db import models'
    yield ''
    yield 'class %s(models.Model):' % model_name
    
    layer = data_source[layer_key]        
    
    for width, precision, field in zip(layer.field_widths, layer.field_precisions, layer.fields):
        feature = layer[0]
        fld_type = feature[field].type_name
        mfield = field.lower()
        
        if mfield[-1:] == '_':
            mfield += 'field'
        
        if fld_type == 'Real':
            yield '    %s = models.DecimalField(max_digits=%s, decimal_places=%s)' % (mfield, width, precision)
        elif fld_type == 'Integer':
            yield '    %s = models.IntegerField()' % mfield
        elif fld_type == 'String':
            yield '    %s = models.CharField(max_length=%s)' % (mfield, width)
        elif fld_type == 'Date':
            yield '    %s = models.DateField()' % mfield
        elif fld_type == 'DateTime':
            yield '    %s = models.DateTimeField()' % mfield
        elif fld_type == 'Time':
            yield '    %s = models.TimeField()' % mfield
        else:
            raise Exception('Unknown field type %s in %s' % (fld_type, mfield))
    
    # Getting the geometry type
    gtype = layer.geom_type
    
    # Setting up the SRID parameter string.
    if srid is None:
        if layer.srs is None:
            srid_str = 'srid=-1'
        else:
            srid = layer.srs.srid
            if srid is None:
                srid_str = 'srid=-1'
            elif srid == 4326:
                # WGS84 is the default.
                srid_str = ''
            else:
                srid_str = 'srid=%s' % srid
    else:
        srid_str = 'srid=%s' % srid

    yield '    %s = models.%s(%s)' % (geom_name, gtype.django, srid_str)
    yield '    objects = models.GeoManager()'
