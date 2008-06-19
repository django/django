import os, sys
from optparse import make_option
from django.contrib.gis import gdal
from django.contrib.gis.management.base import ArgsCommand, CommandError

def layer_option(option, opt, value, parser):
    """
    Callback for `make_option` for the `ogrinspect` `layer_key`
    keyword option which may be an integer or a string.
    """
    try:
        dest = int(value)
    except ValueError:
        dest = value
    setattr(parser.values, option.dest, dest)

def list_option(option, opt, value, parser):
    """
    Callback for `make_option` for `ogrinspect` keywords that require
    a string list.  If the string is 'True'/'true' then the option 
    value will be a boolean instead.
    """
    if value.lower() == 'true':
        dest = True
    else:
        dest = [s for s in value.split(',')]
    setattr(parser.values, option.dest, dest)
    
class Command(ArgsCommand):
    help = ('Inspects the given OGR-compatible data source (e.g., a shapefile) and outputs\n'
            'a GeoDjango model with the given model name. For example:\n'
            ' ./manage.py ogrinspect zipcode.shp Zipcode')
    args = '[data_source] [model_name]'

    option_list = ArgsCommand.option_list + (
        make_option('--blank', dest='blank', type='string', action='callback',  
                    callback=list_option, default=False,
                    help='Use a comma separated list of OGR field names to add '
                    'the `blank=True` option to the field definition.  Set with'
                    '`true` to apply to all applicable fields.'),
        make_option('--decimal', dest='decimal', type='string', action='callback', 
                    callback=list_option, default=False,
                    help='Use a comma separated list of OGR float fields to '
                    'generate `DecimalField` instead of the default '
                    '`FloatField`. Set to `true` to apply to all OGR float fields.'),
        make_option('--geom-name', dest='geom_name', type='string', default='geom',
                    help='Specifies the model name for the Geometry Field '
                    '(defaults to `geom`)'),
        make_option('--layer', dest='layer_key', type='string', action='callback', 
                    callback=layer_option, default=0,
                    help='The key for specifying which layer in the OGR data '
                    'source to use. Defaults to 0 (the first layer). May be '
                    'an integer or a string identifier for the layer.'),
        make_option('--multi-geom', action='store_true', dest='multi_geom', default=False,
                    help='Treat the geometry in the data source as a geometry collection.'),
        make_option('--name-field', dest='name_field',
                    help='Specifies a field name to return for the `__unicode__` function.'),
        make_option('--no-imports', action='store_false', dest='imports', default=True,
                    help='Do not include `from django.contrib.gis.db import models` '
                    'statement.'),
        make_option('--null', dest='null', type='string', action='callback',  
                    callback=list_option, default=False,
                    help='Use a comma separated list of OGR field names to add '
                    'the `null=True` option to the field definition.  Set with'
                    '`true` to apply to all applicable fields.'),
        make_option('--srid', dest='srid',
                    help='The SRID to use for the Geometry Field.  If it can be '
                    'determined, the SRID of the data source is used.'),
        make_option('--mapping', action='store_true', dest='mapping',
                    help='Generate mapping dictionary for use with `LayerMapping`.')
        )

    requires_model_validation = False

    def handle_args(self, *args, **options):
        try:
            data_source, model_name = args
        except ValueError:
            raise CommandError('Invalid arguments, must provide: %s' % self.args)

        if not gdal.HAS_GDAL:
            raise CommandError('GDAL is required to inspect geospatial data sources.')

        # TODO: Support non file-based OGR datasources.
        if not os.path.isfile(data_source):
            raise CommandError('The given data source cannot be found: "%s"' % data_source)
        
        # Removing options with `None` values.
        options = dict([(k, v) for k, v in options.items() if not v is None])

        # Getting the OGR DataSource from the string parameter.
        try:
            ds = gdal.DataSource(data_source)
        except gdal.OGRException, msg:
            raise CommandError(msg)

        # Whether the user wants to generate the LayerMapping dictionary as well.
        show_mapping = options.pop('mapping', False)

        # Returning the output of ogrinspect with the given arguments
        # and options.
        from django.contrib.gis.utils.ogrinspect import _ogrinspect, mapping
        output = [s for s in _ogrinspect(ds, model_name, **options)]
        if show_mapping:
            # Constructing the keyword arguments for `mapping`, and
            # calling it on the data source.
            kwargs = {'geom_name' : options['geom_name'],
                      'layer_key' : options['layer_key'],
                      'multi_geom' : options['multi_geom'],
                      }
            mapping_dict = mapping(ds, **kwargs)
            # This extra legwork is so that the dictionary definition comes
            # out in the same order as the fields in the model definition.
            rev_mapping = dict([(v, k) for k, v in mapping_dict.items()])
            output.extend(['', '# Auto-generated `LayerMapping` dictionary for %s model' % model_name, 
                           '%s_mapping = {' % model_name.lower()])
            output.extend(["    '%s' : '%s'," % (rev_mapping[ogr_fld], ogr_fld) for ogr_fld in ds[options['layer_key']].fields])
            output.extend(["    '%s' : '%s'," % (options['geom_name'], mapping_dict[options['geom_name']]), '}'])
        return '\n'.join(output)
