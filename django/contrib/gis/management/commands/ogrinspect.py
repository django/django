import argparse
import inspect

from django.contrib.gis import gdal
from django.core.management.base import BaseCommand, CommandError


class LayerOptionAction(argparse.Action):
    """
    Custom argparse action for the `ogrinspect` `layer_key` keyword option
    which may be an integer or a string.
    """
    def __call__(self, parser, namespace, value, option_string=None):
        try:
            setattr(namespace, self.dest, int(value))
        except ValueError:
            setattr(namespace, self.dest, value)


class ListOptionAction(argparse.Action):
    """
    Custom argparse action for `ogrinspect` keywords that require
    a string list. If the string is 'True'/'true' then the option
    value will be a boolean instead.
    """
    def __call__(self, parser, namespace, value, option_string=None):
        if value.lower() == 'true':
            setattr(namespace, self.dest, True)
        else:
            setattr(namespace, self.dest, value.split(','))


class Command(BaseCommand):
    help = ('Inspects the given OGR-compatible data source (e.g., a shapefile) and outputs\n'
            'a GeoDjango model with the given model name. For example:\n'
            ' ./manage.py ogrinspect zipcode.shp Zipcode')

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('data_source', help='Path to the data source.')
        parser.add_argument('model_name', help='Name of the model to create.')
        parser.add_argument('--blank', dest='blank',
            action=ListOptionAction, default=False,
            help='Use a comma separated list of OGR field names to add '
            'the `blank=True` option to the field definition. Set to `true` '
            'to apply to all applicable fields.')
        parser.add_argument('--decimal', dest='decimal',
            action=ListOptionAction, default=False,
            help='Use a comma separated list of OGR float fields to '
            'generate `DecimalField` instead of the default '
            '`FloatField`. Set to `true` to apply to all OGR float fields.')
        parser.add_argument('--geom-name', dest='geom_name', default='geom',
            help='Specifies the model name for the Geometry Field '
            '(defaults to `geom`)')
        parser.add_argument('--layer', dest='layer_key',
            action=LayerOptionAction, default=0,
            help='The key for specifying which layer in the OGR data '
            'source to use. Defaults to 0 (the first layer). May be '
            'an integer or a string identifier for the layer.')
        parser.add_argument('--multi-geom', action='store_true',
            dest='multi_geom', default=False,
            help='Treat the geometry in the data source as a geometry collection.')
        parser.add_argument('--name-field', dest='name_field',
            help='Specifies a field name to return for the `__unicode__`/`__str__` function.')
        parser.add_argument('--no-imports', action='store_false', dest='imports', default=True,
            help='Do not include `from django.contrib.gis.db import models` statement.')
        parser.add_argument('--null', dest='null', action=ListOptionAction, default=False,
            help='Use a comma separated list of OGR field names to add '
            'the `null=True` option to the field definition. Set to `true` '
            'to apply to all applicable fields.')
        parser.add_argument('--srid', dest='srid',
            help='The SRID to use for the Geometry Field. If it can be '
            'determined, the SRID of the data source is used.')
        parser.add_argument('--mapping', action='store_true', dest='mapping',
            help='Generate mapping dictionary for use with `LayerMapping`.')

    def handle(self, *args, **options):
        data_source, model_name = options.pop('data_source'), options.pop('model_name')
        if not gdal.HAS_GDAL:
            raise CommandError('GDAL is required to inspect geospatial data sources.')

        # Getting the OGR DataSource from the string parameter.
        try:
            ds = gdal.DataSource(data_source)
        except gdal.GDALException as msg:
            raise CommandError(msg)

        # Returning the output of ogrinspect with the given arguments
        # and options.
        from django.contrib.gis.utils.ogrinspect import _ogrinspect, mapping
        # Filter options to params accepted by `_ogrinspect`
        ogr_options = {k: v for k, v in options.items()
                       if k in inspect.getargspec(_ogrinspect).args and v is not None}
        output = [s for s in _ogrinspect(ds, model_name, **ogr_options)]

        if options['mapping']:
            # Constructing the keyword arguments for `mapping`, and
            # calling it on the data source.
            kwargs = {'geom_name': options['geom_name'],
                      'layer_key': options['layer_key'],
                      'multi_geom': options['multi_geom'],
                      }
            mapping_dict = mapping(ds, **kwargs)
            # This extra legwork is so that the dictionary definition comes
            # out in the same order as the fields in the model definition.
            rev_mapping = {v: k for k, v in mapping_dict.items()}
            output.extend(['', '# Auto-generated `LayerMapping` dictionary for %s model' % model_name,
                           '%s_mapping = {' % model_name.lower()])
            output.extend("    '%s' : '%s'," % (
                rev_mapping[ogr_fld], ogr_fld) for ogr_fld in ds[options['layer_key']].fields
            )
            output.extend(["    '%s' : '%s'," % (options['geom_name'], mapping_dict[options['geom_name']]), '}'])
        return '\n'.join(output) + '\n'
