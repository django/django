from itertools import izip
from django.db.models.query import sql
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey

from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.sql import aggregates as gis_aggregates_module
from django.contrib.gis.db.models.sql.conversion import AreaField, DistanceField, GeomField
from django.contrib.gis.db.models.sql.where import GeoWhereNode
from django.contrib.gis.measure import Area, Distance

# Valid GIS query types.
ALL_TERMS = sql.constants.QUERY_TERMS.copy()
ALL_TERMS.update(SpatialBackend.gis_terms)

TABLE_NAME = sql.constants.TABLE_NAME

class GeoQuery(sql.Query):
    """
    A single spatial SQL query.
    """
    # Overridding the valid query terms.
    query_terms = ALL_TERMS
    aggregates_module = gis_aggregates_module

    #### Methods overridden from the base Query class ####
    def __init__(self, model, conn):
        super(GeoQuery, self).__init__(model, conn, where=GeoWhereNode)
        # The following attributes are customized for the GeoQuerySet.
        # The GeoWhereNode and SpatialBackend classes contain backend-specific
        # routines and functions.
        self.custom_select = {}
        self.transformed_srid = None
        self.extra_select_fields = {}

    def clone(self, *args, **kwargs):
        obj = super(GeoQuery, self).clone(*args, **kwargs)
        # Customized selection dictionary and transformed srid flag have
        # to also be added to obj.
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
        result = ['(%s) AS %s' % (self.get_extra_select_format(alias) % col[0], qn2(alias))
                  for alias, col in self.extra_select.iteritems()]
        aliases = set(self.extra_select.keys())
        if with_aliases:
            col_aliases = aliases.copy()
        else:
            col_aliases = set()
        if self.select:
            only_load = self.deferred_to_columns()
            # This loop customized for GeoQuery.
            for col, field in izip(self.select, self.select_fields):
                if isinstance(col, (list, tuple)):
                    alias, column = col
                    table = self.alias_map[alias][TABLE_NAME]
                    if table in only_load and col not in only_load[table]:
                        continue
                    r = self.get_field_select(field, alias, column)
                    if with_aliases:
                        if col[1] in col_aliases:
                            c_alias = 'Col%d' % len(col_aliases)
                            result.append('%s AS %s' % (r, c_alias))
                            aliases.add(c_alias)
                            col_aliases.add(c_alias)
                        else:
                            result.append('%s AS %s' % (r, qn2(col[1])))
                            aliases.add(r)
                            col_aliases.add(col[1])
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

        result.extend([
                '%s%s' % (
                    self.get_extra_select_format(alias) % aggregate.as_sql(quote_func=qn),
                    alias is not None and ' AS %s' % alias or ''
                    )
                for alias, aggregate in self.aggregate_select.items()
        ])

        # This loop customized for GeoQuery.
        for (table, col), field in izip(self.related_select_cols, self.related_select_fields):
            r = self.get_field_select(field, table, col)
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
        model. Will sometimes be called to pull in related models (e.g. via
        select_related), in which case "opts" and "start_alias" will be given
        to provide a starting point for the traversal.

        Returns a list of strings, quoted appropriately for use in SQL
        directly, as well as a set of aliases used in the select statement (if
        'as_pairs' is True, returns a list of (alias, col_name) pairs instead
        of strings as the first component and None as the second component).

        This routine is overridden from Query to handle customized selection of
        geometry columns.
        """
        result = []
        if opts is None:
            opts = self.model._meta
        aliases = set()
        only_load = self.deferred_to_columns()
        proxied_model = opts.proxy and opts.proxy_for_model or 0
        if start_alias:
            seen = {None: start_alias}
        for field, model in opts.get_fields_with_model():
            if start_alias:
                try:
                    alias = seen[model]
                except KeyError:
                    if model is proxied_model:
                        alias = start_alias
                    else:
                        link_field = opts.get_ancestor_link(model)
                        alias = self.join((start_alias, model._meta.db_table,
                                           link_field.column, model._meta.pk.column))
                    seen[model] = alias
            else:
                # If we're starting from the base model of the queryset, the
                # aliases will have already been set up in pre_sql_setup(), so
                # we can save time here.
                alias = self.included_inherited_models[model]
            table = self.alias_map[alias][TABLE_NAME]
            if table in only_load and field.column not in only_load[table]:
                continue
            if as_pairs:
                result.append((alias, field.column))
                aliases.add(alias)
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
        return result, aliases

    def resolve_columns(self, row, fields=()):
        """
        This routine is necessary so that distances and geometries returned
        from extra selection SQL get resolved appropriately into Python
        objects.
        """
        values = []
        aliases = self.extra_select.keys()

        # Have to set a starting row number offset that is used for
        # determining the correct starting row index -- needed for
        # doing pagination with Oracle.
        rn_offset = 0
        if SpatialBackend.oracle:
            if self.high_mark is not None or self.low_mark: rn_offset = 1
        index_start = rn_offset + len(aliases)

        # Converting any extra selection values (e.g., geometries and
        # distance objects added by GeoQuerySet methods).
        values = [self.convert_values(v, self.extra_select_fields.get(a, None))
                  for v, a in izip(row[rn_offset:index_start], aliases)]
        if SpatialBackend.oracle or getattr(self, 'geo_values', False):
            # We resolve the rest of the columns if we're on Oracle or if
            # the `geo_values` attribute is defined.
            for value, field in izip(row[index_start:], fields):
                values.append(self.convert_values(value, field))
        else:
            values.extend(row[index_start:])
        return values

    def convert_values(self, value, field):
        """
        Using the same routines that Oracle does we can convert our
        extra selection objects into Geometry and Distance objects.
        TODO: Make converted objects 'lazy' for less overhead.
        """
        if SpatialBackend.oracle:
            # Running through Oracle's first.
            value = super(GeoQuery, self).convert_values(value, field or GeomField())

        if isinstance(field, DistanceField):
            # Using the field's distance attribute, can instantiate
            # `Distance` with the right context.
            value = Distance(**{field.distance_att : value})
        elif isinstance(field, AreaField):
            value = Area(**{field.area_att : value})
        elif isinstance(field, (GeomField, GeometryField)) and value:
            value = SpatialBackend.Geometry(value)
        return value

    def resolve_aggregate(self, value, aggregate):
        """
        Overridden from GeoQuery's normalize to handle the conversion of
        GeoAggregate objects.
        """
        if isinstance(aggregate, self.aggregates_module.GeoAggregate):
            if aggregate.is_extent:
                return self.aggregates_module.convert_extent(value)
            else:
                return self.aggregates_module.convert_geom(value, aggregate.source)
        else:
            return super(GeoQuery, self).resolve_aggregate(value, aggregate)

    #### Routines unique to GeoQuery ####
    def get_extra_select_format(self, alias):
        sel_fmt = '%s'
        if alias in self.custom_select:
            sel_fmt = sel_fmt % self.custom_select[alias]
        return sel_fmt

    def get_field_select(self, field, alias=None, column=None):
        """
        Returns the SELECT SQL string for the given field.  Figures out
        if any custom selection SQL is needed for the column  The `alias`
        keyword may be used to manually specify the database table where
        the column exists, if not in the model associated with this
        `GeoQuery`.  Similarly, `column` may be used to specify the exact
        column name, rather than using the `column` attribute on `field`.
        """
        sel_fmt = self.get_select_format(field)
        if field in self.custom_select:
            field_sel = sel_fmt % self.custom_select[field]
        else:
            field_sel = sel_fmt % self._field_column(field, alias, column)
        return field_sel

    def get_select_format(self, fld):
        """
        Returns the selection format string, depending on the requirements
        of the spatial backend.  For example, Oracle and MySQL require custom
        selection formats in order to retrieve geometries in OGC WKT. For all
        other fields a simple '%s' format string is returned.
        """
        if SpatialBackend.select and hasattr(fld, 'geom_type'):
            # This allows operations to be done on fields in the SELECT,
            # overriding their values -- used by the Oracle and MySQL
            # spatial backends to get database values as WKT, and by the
            # `transform` method.
            sel_fmt = SpatialBackend.select

            # Because WKT doesn't contain spatial reference information,
            # the SRID is prefixed to the returned WKT to ensure that the
            # transformed geometries have an SRID different than that of the
            # field -- this is only used by `transform` for Oracle and
            # SpatiaLite backends.
            if self.transformed_srid and ( SpatialBackend.oracle or
                                           SpatialBackend.spatialite ):
                sel_fmt = "'SRID=%d;'||%s" % (self.transformed_srid, sel_fmt)
        else:
            sel_fmt = '%s'
        return sel_fmt

    # Private API utilities, subject to change.
    def _field_column(self, field, table_alias=None, column=None):
        """
        Helper function that returns the database column for the given field.
        The table and column are returned (quoted) in the proper format, e.g.,
        `"geoapp_city"."point"`.  If `table_alias` is not specified, the
        database table associated with the model of this `GeoQuery` will be
        used.  If `column` is specified, it will be used instead of the value
        in `field.column`.
        """
        if table_alias is None: table_alias = self.model._meta.db_table
        return "%s.%s" % (self.quote_name_unless_alias(table_alias),
                          self.connection.ops.quote_name(column or field.column))

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
            return GeoWhereNode._check_geo_field(self.model._meta, field_name)
