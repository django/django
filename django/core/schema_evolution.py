import django
from django.core.exceptions import ImproperlyConfigured
from optparse import OptionParser
from django.utils import termcolors
from django.conf import settings
import os, re, shutil, sys, textwrap
import management


def get_sql_evolution_check_for_new_fields(klass, new_table_name):
    "checks for model fields that are not in the existing data structure"
    from django.db import backend, get_creation_module, models, get_introspection_module, connection
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
    introspection = get_introspection_module()
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    for f in opts.fields:
        existing_fields = introspection.get_columns(cursor,db_table)
        if f.column not in existing_fields and (not f.aka or f.aka not in existing_fields and len(set(f.aka) & set(existing_fields))==0):
            rel_field = f
            data_type = f.get_internal_type()
            col_type = data_types.get(data_type)
            if col_type is not None:
                output.extend( backend.get_add_column_sql( klass._meta.db_table, f.column, management.style.SQL_COLTYPE(col_type % rel_field.__dict__), f.null, f.unique, f.primary_key, f.default ) )
    return output

def get_sql_evolution_check_for_changed_model_name(klass):
    from django.db import backend, get_creation_module, models, get_introspection_module, connection
    cursor = connection.cursor()
    introspection = get_introspection_module()
    table_list = introspection.get_table_list(cursor)
    if klass._meta.db_table in table_list:
        return [], None
    if klass._meta.aka in table_list:
        return backend.get_change_table_name_sql( klass._meta.db_table, klass._meta.aka), klass._meta.aka
    elif len(set(klass._meta.aka) & set(table_list))==1:
        return backend.get_change_table_name_sql( klass._meta.db_table, klass._meta.aka[0]), klass._meta.aka[0]
    else:
        return [], None
    
def get_sql_evolution_check_for_changed_field_name(klass, new_table_name):
    from django.db import backend, get_creation_module, models, get_introspection_module, connection
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
    introspection = get_introspection_module()
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    for f in opts.fields:
        existing_fields = introspection.get_columns(cursor,db_table)
        if f.column not in existing_fields and f.aka and (f.aka in existing_fields or len(set(f.aka) & set(existing_fields)))==1:
            old_col = None
            if isinstance( f.aka, str ):
                old_col = f.aka
            else:
                old_col = f.aka[0]
            rel_field = f
            data_type = f.get_internal_type()
            col_type = data_types[data_type]
            if col_type is not None:
                col_def = management.style.SQL_COLTYPE(col_type % rel_field.__dict__) +' '+ management.style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or ''))
                if f.unique:
                    col_def += management.style.SQL_KEYWORD(' UNIQUE')
                if f.primary_key:
                    col_def += management.style.SQL_KEYWORD(' PRIMARY KEY')
                output.extend( backend.get_change_column_name_sql( klass._meta.db_table, introspection.get_indexes(cursor,db_table), old_col, f.column, col_def ) )
    return output
    
def get_sql_evolution_check_for_changed_field_flags(klass, new_table_name):
    from django.db import backend, get_creation_module, models, get_introspection_module, connection
    from django.db.models.fields import CharField, SlugField
    from django.db.models.fields.related import RelatedField, ForeignKey
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
    introspection = get_introspection_module()
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    for f in opts.fields:
        existing_fields = introspection.get_columns(cursor,db_table)
#        print existing_fields
        cf = None # current field, ie what it is before any renames
        if f.column in existing_fields:
            cf = f.column
        elif f.aka in existing_fields:
            cf = f.aka
        elif f.aka and len(set(f.aka) & set(existing_fields))==1:
            cf = f.aka[0]
        else:
            continue # no idea what column you're talking about - should be handled by get_sql_evolution_check_for_new_fields())
        data_type = f.get_internal_type()
        if data_types.has_key(data_type):
            column_flags = introspection.get_known_column_flags(cursor, db_table, cf)
#            print db_table, cf, column_flags
            if column_flags['allow_null']!=f.null or \
                    ( not f.primary_key and isinstance(f, CharField) and column_flags['maxlength']!=str(f.maxlength) ) or \
                    ( not f.primary_key and isinstance(f, SlugField) and column_flags['maxlength']!=str(f.maxlength) ) or \
                    ( column_flags['unique']!=f.unique and ( settings.DATABASE_ENGINE!='postgresql' or not f.primary_key ) ) or \
                    column_flags['primary_key']!=f.primary_key:
                    #column_flags['foreign_key']!=f.foreign_key:
#                print 'need to change'
#                print db_table, f.column, column_flags
#                print "column_flags['allow_null']!=f.null", column_flags['allow_null']!=f.null
#                print "not f.primary_key and isinstance(f, CharField) and column_flags['maxlength']!=str(f.maxlength)", not f.primary_key and isinstance(f, CharField) and column_flags['maxlength']!=str(f.maxlength)
#                print "not f.primary_key and isinstance(f, SlugField) and column_flags['maxlength']!=str(f.maxlength)", not f.primary_key and isinstance(f, SlugField) and column_flags['maxlength']!=str(f.maxlength)
#                print "column_flags['unique']!=f.unique", column_flags['unique']!=f.unique
#                print "column_flags['primary_key']!=f.primary_key", column_flags['primary_key']!=f.primary_key
                col_type = data_types[data_type]
                col_type_def = management.style.SQL_COLTYPE(col_type % f.__dict__)
#                col_def = style.SQL_COLTYPE(col_type % f.__dict__) +' '+ style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or ''))
#                if f.unique:
#                    col_def += ' '+ style.SQL_KEYWORD('UNIQUE')
#                if f.primary_key:
#                    col_def += ' '+ style.SQL_KEYWORD('PRIMARY KEY')
                output.extend( backend.get_change_column_def_sql( klass._meta.db_table, cf, col_type_def, f.null, f.unique, f.primary_key, f.default ) )
                    #print db_table, cf, f.maxlength, introspection.get_known_column_flags(cursor, db_table, cf)
    return output

def get_sql_evolution_check_for_dead_fields(klass, new_table_name):
    from django.db import backend, get_creation_module, models, get_introspection_module, connection
    from django.db.models.fields import CharField, SlugField
    from django.db.models.fields.related import RelatedField, ForeignKey
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
    introspection = get_introspection_module()
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    suspect_fields = set(introspection.get_columns(cursor,db_table))
#    print 'suspect_fields = ', suspect_fields
    for f in opts.fields:
#        print 'f = ', f
#        print 'f.aka = ', f.aka
        suspect_fields.discard(f.column)
        suspect_fields.discard(f.aka)
        if f.aka: suspect_fields.difference_update(f.aka)
    if len(suspect_fields)>0:
        output.append( '-- warning: the following may cause data loss' )
        for suspect_field in suspect_fields:
            output.extend( backend.get_drop_column_sql( klass._meta.db_table, suspect_field ) )
        output.append( '-- end warning' )
    return output

