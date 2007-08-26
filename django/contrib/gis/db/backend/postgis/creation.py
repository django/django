from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test.utils import _set_autocommit, TEST_DATABASE_PREFIX
from commands import getstatusoutput
import os, re, sys

def create_lang(db_name, verbosity=1):
    "This sets up the pl/pgsql language on the given database."

    # Getting the command-line options for the shell command
    options = get_cmd_options(db_name)

    # Constructing the 'createlang' command.
    createlang_cmd = 'createlang %splpgsql' % options
    if verbosity >= 1: print createlang_cmd

    # Must have database super-user privileges to execute createlang -- it must
    #  also be in your path.
    status, output = getstatusoutput(createlang_cmd)

    # Checking the status of the command, 0 => execution successful
    if status != 0:
        raise Exception, "Error executing 'plpgsql' command: %s\n" % output

def _create_with_cursor(db_name, verbosity=1, autoclobber=False):
    "Creates database with psycopg2 cursor."

    # Constructing the necessary SQL to create the database (the DATABASE_USER
    #  must possess the privileges to create a database)
    create_sql = 'CREATE DATABASE %s OWNER %s' % (connection.ops.quote_name(db_name),
                                                  settings.DATABASE_USER)
    cursor = connection.cursor()
    _set_autocommit(connection)

    try:
        # Trying to create the database first.
        cursor.execute(create_sql)
    except Exception, e:
        # Drop and recreate, if necessary.
        if not autoclobber:
            confirm = raw_input("\nIt appears the database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % db_name)
        if autoclobber or confirm == 'yes':
            if verbosity >= 1: print 'Destroying old spatial database...'
            drop_db(db_name)
            if verbosity >= 1: print 'Creating new spatial database...'
            cursor.execute(create_sql)
        else:
            raise Exception, 'Spatial Database Creation canceled.'
    
created_regex = re.compile(r'^createdb: database creation failed: ERROR:  database ".+" already exists')
def _create_with_shell(db_name, verbosity=1, autoclobber=False):
    """If no spatial database already exists, then using a cursor will not work.  Thus, a
    `createdb` command will be issued through the shell to bootstrap the database."""

    # Getting the command-line options for the shell command
    options = get_cmd_options(False)
    create_cmd = 'createdb -O %s %s%s' % (settings.DATABASE_USER, options, db_name)
    if verbosity >= 1: print create_cmd

    # Attempting to create the database.
    status, output = getstatusoutput(create_cmd)
    if status != 0:
        if created_regex.match(output):
            if not autoclobber:
                confirm = raw_input("\nIt appears the database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % db_name)
            if autoclobber or confirm == 'yes':
                if verbosity >= 1: print 'Destroying old spatial database...'
                drop_cmd = 'dropdb %s%s' % (options, db_name)
                status, output = getstatusoutput(drop_cmd)
                if status != 0: 
                    raise Exception, 'Could not drop database %s: %s' % (db_name, output)
                if verbosity >= 1: print 'Creating new spatial database...'
                status, output = getstatusoutput(create_cmd)
                if status != 0:
                    raise Exception, 'Could not create database after dropping: %s' % output
            else:
                raise Exception, 'Spatial Database Creation canceled.'
        else:
            raise Exception, 'Unknown error occurred in creating database: %s' % output

def create_spatial_db(test=False, verbosity=1, autoclobber=False, interactive=False):
    "This Python routine creates a spatial database based on settings.py."

    # Making sure we're using PostgreSQL and psycopg2
    if settings.DATABASE_ENGINE != 'postgresql_psycopg2':
        raise Exception, 'Spatial database creation only supported postgresql_psycopg2 platform.'

    # This routine depends on getstatusoutput(), which does not work on Windows.
    # TODO: Consider executing shell commands with popen for Windows compatibility
    if os.name == 'nt':
        raise Exception, 'Automatic spatial database creation only supported on *NIX platforms.'

    # Getting the spatial database name
    if test: 
        db_name = get_spatial_db(test=True)
        _create_with_cursor(db_name, verbosity=verbosity, autoclobber=autoclobber)
    else: 
        db_name = get_spatial_db()
        _create_with_shell(db_name, verbosity=verbosity, autoclobber=autoclobber)

    # Creating the db language.
    create_lang(db_name, verbosity=verbosity)

    # Now adding in the PostGIS routines.
    load_postgis_sql(db_name, verbosity=verbosity)

    if verbosity >= 1: print 'Creation of spatial database %s successful.' % db_name

    # Closing the connection
    connection.close()
    settings.DATABASE_NAME = db_name

    # Syncing the database
    call_command('syncdb', verbosity=verbosity, interactive=interactive)

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()
    
def drop_db(db_name=False, test=False):
    "Using the cursor, drops the given database.  All exceptions will be propagated up."
    if not db_name: db_name = get_spatial_db(test=test)
    cursor = connection.cursor()
    cursor.execute("DROP DATABASE %s" % connection.ops.quote_name(db_name))

def get_cmd_options(db_name):
    "Obtains the command-line PostgreSQL connection options for shell commands."
    # The db_name parameter is optional
    if db_name:
        options = '-d %s -U %s ' % (db_name, settings.DATABASE_USER)
    else:
        options = '-U %s ' % settings.DATABASE_USER
    if settings.DATABASE_HOST:
        options += '-h %s ' % settings.DATABASE_HOST
    if settings.DATABASE_PORT:
        options += '-p %s ' % settings.DATABASE_PORT
    return options

def get_spatial_db(test=False):
    """This routine returns the name of the spatial database.
    Set the 'test' keyword for the test spatial database name."""
    if test:
        if settings.TEST_DATABASE_NAME:
            test_db_name = settings.TEST_DATABASE_NAME
        else:
            test_db_name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
        return test_db_name
    else:
        if not settings.DATABASE_NAME:
            raise Exception, 'must configure DATABASE_NAME in settings.py'
        return settings.DATABASE_NAME

def load_postgis_sql(db_name, verbosity=1):
    "This routine loads up the PostGIS SQL files lwpostgis.sql and spatial_ref_sys.sql."

    # Getting the path to the PostGIS SQL
    try:
        # POSTGIS_SQL_PATH may be placed in settings to tell GeoDjango where the 
        #   PostGIS SQL files are located
        sql_path = settings.POSTGIS_SQL_PATH
    except AttributeError:
        sql_path = '/usr/local/share'

    # The PostGIS SQL post-creation files.
    lwpostgis_file = os.path.join(sql_path, 'lwpostgis.sql')
    srefsys_file   = os.path.join(sql_path, 'spatial_ref_sys.sql')
    if not os.path.isfile(lwpostgis_file):
        raise Exception, 'Could not find PostGIS function definitions in %s' % lwpostgis_file
    if not os.path.isfile(srefsys_file):
        raise Exception, 'Could not find PostGIS spatial reference system definitions in %s' % srefsys_file

    # Getting the psql command-line options.
    options = get_cmd_options(db_name)
    
    # Now trying to load up the PostGIS functions
    cmd = 'psql %s-f %s' % (options, lwpostgis_file)
    if verbosity >= 1: print cmd
    status, output = getstatusoutput(cmd)
    if status != 0:
        raise Exception, 'Error in loading PostGIS lwgeometry routines.'

    # Now trying to load up the Spatial Reference System table
    cmd = 'psql %s-f %s' % (options, srefsys_file)
    if verbosity >= 1: print cmd
    status, output = getstatusoutput(cmd)
    if status !=0:
        raise Exception, 'Error in loading PostGIS spatial_ref_sys table.'
    
