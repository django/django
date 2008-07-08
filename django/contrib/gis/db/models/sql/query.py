from itertools import izip
from django.db.models.query import sql
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey

from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.sql.where import GeoWhereNode
from django.contrib.gis.measure import Area, Distance

# Valid GIS query types.
ALL_TERMS = sql.constants.QUERY_TERMS.copy()
ALL_TERMS.update(SpatialBackend.gis_terms)

class GeoQuery(sql.Query):
    """
    A single spatial SQL query.
    """
    # Overridding the valid query terms.
    query_terms = ALL_TERMS

    #### Methods overridden from the base Query class ####
    def __init__(self, model, conn):
        super(GeoQuery, self).__init__(model, conn, where=GeoWhereNode)
        # The following attributes are customized for the GeoQuerySet.
        # The GeoWhereNode and SpatialBackend classes contain backend-specific
        # routines and functions.
        self.aggregate = False
        self.custom_select = {}
        self.transformed_srid = None
        self.extra_select_fields = {}

    def clone(self, *args, **kwargs):
        obj = super(GeoQuery, self).clone(*args, **kwargs)
        # Customized selection dictionary and transformed srid flag have
        # to also be added to obj.
        obj.aggregate = self.aggregate
        obj.custom_select = self.custom_select.copy()
        obj.transformed_srid = self.transformed_srid
        obj.extra_select_fields = self.extra_select_fields.copy()
        return obj

    def get_columns(self, with_aliases=False):
        """
        Return the list of columns to use in the select statement. If no
        columns have been specified, returns all columns relating to fields in
        the model.

        If 'with_aliases' is true, any column names that are duplicated
        (without the table names) are given unique aliases. This is needed in
        some cases to avoid ambiguitity with nested queries.

        This routine is overridden from Query to handle customized selection of 
        geometry columns.
        """
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        result = ['(%s) AS %s' % (self.get_extra_select_format(alias) % col, qn2(alias)) 
                  for alias, col in self.extra_select.iteritems()]
        aliases = set(self.extra_select.keys())
        if with_aliases:
            col_aliases = aliases.copy()
        else:
            col_aliases = set()
        if self.select:
            # This loop customized for GeoQuery.
            for col, field in izip(self.select, self.select_fields):
                if isinstance(col, (list, tuple)):
                    r = self.get_field_select(field, col[0])
                    if with_aliases and col[1] in col_aliases:
                        c_alias = 'Col%d' % len(col_aliases)
                        result.append('%s AS %s' % (r, c_alias))
                        aliases.add(c_alias)
                        col_aliases.add(c_alias)
                    else:
                        result.append(r)
                        aliases.add(r)
                        col_aliases.add(col[1])
                else:
                    result.append(col.as_sql(quote_func=qn))
                    if hasattr(col, 'alias'):
                        aliases.add(col.alias)
                        col_aliases.add(col.alias)
        elif self.default_cols:
            cols, new_aliases = self.get_default_columns(with_aliases,
                    col_aliases)
            result.extend(cols)
            aliases.update(new_aliases)
        # This loop customized for GeoQuery.
        if not self.aggregate:
            for (table, col), field in izip(self.related_select_cols, self.related_select_fields):
                r = self.get_field_select(field, table)
                if with_aliases and col in col_aliases:
                    c_alias = 'Col%d' % len(col_aliases)
                    result.append('%s AS %s' % (r, c_alias))
                    aliases.add(c_alias)
                    col_aliases.add(c_alias)
                else:
                    result.append(r)
                    aliases.add(r)
                    col_aliases.add(col)

        self._select_aliases = aliases
        return result

    def get_default_columns(self, with_aliases=False, col_aliases=None,
                            start_alias=None, opts=None, as_pairs=False):
        """
        Computes the default columns for selecting every field in the base
        model.

        Returns a list of strings, quoted appropriately for use in SQL
        directly, as well as a set of aliases used in the select statement.

        This routine is overridden from Query to handle customized selection of 
        geometry columns.
        """
        result = []
        if opts is None:
            opts = self.model._meta
        if start_alias:
            table_alias = start_alias
        else:
            table_alias = self.tables[0]
        root_pk = self.model._meta.pk.column
        seen = {None: table_alias}
        aliases = set()
        for field, model in opts.get_fields_with_model():
            try:
                alias = seen[model]
            except KeyError:
                alias = self.join((table_alias, model._meta.db_table,
                        root_pk, model._meta.pk.column))
                seen[model] = alias
            if as_pairs:
                result.append((alias, field.column))
                continue
            # This part of the function is customized for GeoQuery. We
            # see if there was any custom selection specified in the
            # dictionary, and set up the selection format appropriately.
            field_sel = self.get_field_select(field, alias)
            if with_aliases and field.column in col_aliases:
                c_alias = 'Col%d' % len(col_aliases)
                result.append('%s AS %s' % (field_sel, c_alias))
                col_aliases.add(c_alias)
                aliases.add(c_alias)
            else:
                r = field_sel
                result.append(r)
                aliases.add(r)
                if with_aliases:
                    col_aliases.add(field.column)
        if as_pairs:
            return result, None
        return result, aliases

    def get_ordering(self):
        """
        This routine is overridden to disable ordering for aggregate
        spatial queries.
        """
        if not self.aggregate:
            return super(GeoQuery, self).get_ordering()
        else:
            return ()

    def resolve_columns(self, row, fields=()):
        """
        This routine is necessary so that distances and geometries returned
        from extra selection SQL get resolved appropriately into Python 
        objects.
        """
        values = []
        aliases = self.extra_select.keys()
        index_start = len(aliases)
        values = [self.convert_values(v, self.extra_select_fields.get(a, None)) 
                  for v, a in izip(row[:index_start], aliases)]
        if SpatialBackend.oracle:
            # This is what happens normally in Oracle's `resolve_columns`.
            for value, field in izip(row[index_start:], fields):
                values.append(self.convert_values(value, field))
        else:
            values.extend(row[index_start:])
        return values

    def convert_values(self, value, field):
        """
        Using the same routines that Oracle does we can convert our
        extra selection objects into Geometry and Distance objects.
        TODO: Laziness.
        """
        if SpatialBackend.oracle:
            # Running through Oracle's first.
            value = super(GeoQuery, self).convert_values(value, field)
        if isinstance(field, DistanceField):
            # Using the field's distance attribute, can instantiate
            # `Distance` with the right context.
            value = Distance(**{field.distance_att : value})
        elif isinstance(field, AreaField):
            value = Area(**{field.area_att : value})
        elif isinstance(field, GeomField):
            value = SpatialBackend.Geometry(value)
        return value

    #### Routines unique to GeoQuery ####
    def get_extra_select_format(self, alias):
        sel_fmt = '%s'
        if alias in self.custom_select:
            sel_fmt = sel_fmt % self.custom_select[alias]
        return sel_fmt

    def get_field_select(self, fld, alias=None):
        """
        Returns the SELECT SQL string for the given field.  Figures out
        if any custom selection SQL is needed for the column  The `alias` 
        keyword may be used to manually specify the database table where 
        the column exists, if not in the model associated with this 
        `GeoQuery`.
        """
        sel_fmt = self.get_select_format(fld)
        if fld in self.custom_select:
            field_sel = sel_fmt % self.custom_select[fld]
        else:
            field_sel = sel_fmt % self._field_column(fld, alias)
        return field_sel

    def get_select_format(self, fld):
        """
        Returns the selection format string, depending on the requirements
        of the spatial backend.  For example, Oracle and MySQL require custom
        selection formats in order to retrieve geometries in OGC WKT. For all
        other fields a simple '%s' format string is returned.
        """
        if SpatialBackend.select and hasattr(fld, '_geom'):
            # This allows operations to be done on fields in the SELECT,
            # overriding their values -- used by the Oracle and MySQL
            # spatial backends to get database values as WKT, and by the
            # `transform` method.
            sel_fmt = SpatialBackend.select

            # Because WKT doesn't contain spatial reference information,
            # the SRID is prefixed to the returned WKT to ensure that the
            # transformed geometries have an SRID different than that of the
            # field -- this is only used by `transform` for Oracle backends.
            if self.transformed_srid and SpatialBackend.oracle:
                sel_fmt = "'SRID=%d;'||%s" % (self.transformed_srid, sel_fmt)
        else:
            sel_fmt = '%s'
        return sel_fmt

    # Private API utilities, subject to change.
    def _check_geo_field(self, model, name_param):
        """
        Recursive utility routine for checking the given name parameter
        on the given model.  Initially, the name parameter is a string,
        of the field on the given model e.g., 'point', 'the_geom'. 
        Related model field strings like 'address__point', may also be 
        used.

        If a GeometryField exists according to the given name parameter 
        it will be returned, otherwise returns False.
        """
        if isinstance(name_param, basestring):
            # This takes into account the situation where the name is a 
            # lookup to a related geographic field, e.g., 'address__point'.
            name_param = name_param.split(sql.constants.LOOKUP_SEP)
            name_param.reverse() # Reversing so list operates like a queue of related lookups.
        elif not isinstance(name_param, list):
            raise TypeError
        try:
            # Getting the name of the field for the model (by popping the first
            # name from the `name_param` list created above).
            fld, mod, direct, m2m = model._meta.get_field_by_name(name_param.pop())
        except (FieldDoesNotExist, IndexError):
            return False
        # TODO: ManyToManyField?
        if isinstance(fld, GeometryField): 
            return fld # A-OK.
        elif isinstance(fld, ForeignKey):
            # ForeignKey encountered, return the output of this utility called
            # on the _related_ model with the remaining name parameters.
            return self._check_geo_field(fld.rel.to, name_param) # Recurse to check ForeignKey relation.
        else:
            return False

    def _field_column(self, field, table_alias=None):
        """
        Helper function that returns the database column for the given field.
        The table and column are returned (quoted) in the proper format, e.g.,
        `"geoapp_city"."point"`.  If `table_alias` is not specified, the 
        database table associated with the model of this `GeoQuery` will be
        used.
        """
        if table_alias is None: table_alias = self.model._meta.db_table
        return "%s.%s" % (self.quote_name_unless_alias(table_alias), 
                          self.connection.ops.quote_name(field.column))

    def _geo_field(self, field_name=None):
        """
        Returns the first Geometry field encountered; or specified via the
        `field_name` keyword.  The `field_name` may be a string specifying
        the geometry field on this GeoQuery's model, or a lookup string
        to a geometry field via a ForeignKey relation.
        """
        if field_name is None:
            # Incrementing until the first geographic field is found.
            for fld in self.model._meta.fields:
                if isinstance(fld, GeometryField): return fld
            return False
        else:
            # Otherwise, check by the given field name -- which may be
            # a lookup to a _related_ geographic field.
            return self._check_geo_field(self.model, field_name)

### Field Classes for `convert_values` ####
class AreaField(object):
    def __init__(self, area_att):
        self.area_att = area_att

class DistanceField(object):
    def __init__(self, distance_att):
        self.distance_att = distance_att

# Rather than use GeometryField (which requires a SQL query
# upon instantiation), use this lighter weight class.
class GeomField(object): 
    pass
