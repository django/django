DATA_TYPES = {
    'AutoField':                    'number(11)',
    'BooleanField':                 'number(1) CHECK (%(column)s IN (0,1))',
    'CharField':                    'varchar2(%(maxlength)s)',
    'CommaSeparatedIntegerField':   'varchar2(%(maxlength)s)',
    'DateField':                    'date',
    'DateTimeField':                'timestamp with time zone',
    'FileField':                    'varchar2(100)',
    'FilePathField':                'varchar2(100)',
    'FloatField':                   'number(%(max_digits)s, %(decimal_places)s)',
    'ImageField':                   'varchar2(100)',
    'IntegerField':                 'number(11)',
    'IPAddressField':               'char(15)',
    'ManyToManyField':              None,
    'NullBooleanField':             'number(1) CHECK ((%(column)s IN (0,1)) OR (%(column)s IS NULL))',
    'OneToOneField':                'number(11)',
    'PhoneNumberField':             'varchar2(20)',
    'PositiveIntegerField':         'number(11) CHECK (%(column)s >= 1)',
    'PositiveSmallIntegerField':    'number(11) CHECK (%(column)s >= 1)',
    'SlugField':                    'varchar2(50)',
    'SmallIntegerField':            'number(11)',
    'TextField':                    'clob',
    'TimeField':                    'timestamp',
    'URLField':                     'varchar2(200)',
    'USStateField':                 'char(2)',
}

TEST_DATABASE_PREFIX = 'test_'

def create_test_db(settings, connection, backend, verbosity=1, autoclobber=False):
    if verbosity >= 1:
        print "Creating test database..."

    TEST_DATABASE_NAME = _test_database_name(settings)

    cursor = connection.cursor()
    try:
        _create_test_db(cursor, backend.quote_name(TEST_DATABASE_NAME))
    except Exception, e:            
        sys.stderr.write("Got an error creating the test database: %s\n" % e)
        if not autoclobber:
            confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
        if autoclobber or confirm == 'yes':
            try:
                if verbosity >= 1:
                    print "Destroying old test database..."                
                _destroy_test_db(cursor, backend.quote_name(TEST_DATABASE_NAME))
                if verbosity >= 1:
                    print "Creating test database..."
                _create_test_db(cursor, backend.quote_name(TEST_DATABASE_NAME))
            except Exception, e:
                sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                sys.exit(2)
        else:
            print "Tests cancelled."
            sys.exit(1)
               
    connection.close()
    settings.DATABASE_NAME = TEST_DATABASE_NAME

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()
	
def destroy_test_db(settings, connection, backend, old_database_name, verbosity=1):
    if verbosity >= 1:
        print "Destroying test database..."
    connection.close()

    TEST_DATABASE_NAME = _test_database_name(settings)
    settings.DATABASE_NAME = old_database_name

    cursor = connection.cursor()
    time.sleep(1) # To avoid "database is being accessed by other users" errors.
    _destroy_test_db(cursor, backend.quote_name(TEST_DATABASE_NAME))
    connection.close()

def _create_test_db(cursor, dbname):
    statements = [
	"""create tablespace %(user)s
           datafile '%(user)s.dat' size 10M autoextend on next 10M  maxsize 20M
	""",
	"""create temporary tablespace %(user)s_temp
	   tempfile '%(user)s_temp.dat' size 10M autoextend on next 10M  maxsize 20M
	""",
	"""create user %(user)s
           identified by %(password)s
           default tablespace %(user)s
           temporary tablespace %(user)s_temp
        """,
	"""grant resource to %(user)s""",
	"""grant connect to %(user)s""",
    ]
    _execute_statements(cursor, statements, dbname)
    
def _destroy_test_db(cursor, dbname):
    statements = [
	"""drop user %(user)s cascade""",
	"""drop tablespace %(user)s including contents and datafiles cascade constraints""",
	"""drop tablespace %(user)s_temp including contents and datafiles cascade constraints""",
	]
    _execute_statements(cursor, statements, dbname)

def _execute_statements(cursor, statements, dbname):
    for template in statements:
	stmt = template % {'user': dbname, 'password': "Im a lumberjack"}
	if verbosity >= 1:
	    print stmt
	try:
	    cursor.execute(stmt)
	except Exception, err:
	    sys.stderr.write("Failed (%s)\n" % (err))
	    if required:
		raise

def _test_database_name(settings):
    if settings.TEST_DATABASE_NAME:
	name = settings.TEST_DATABASE_NAME
    else:
	name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
    
