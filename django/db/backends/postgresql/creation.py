# This dictionary maps Field objects to their associated PostgreSQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'serial',
    'BooleanField':      'boolean',
    'CharField':         'varchar(%(max_length)s)',
    'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
    'DateField':         'date',
    'DateTimeField':     'timestamp with time zone',
    'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
    'FileField':         'varchar(%(max_length)s)',
    'FilePathField':     'varchar(%(max_length)s)',
    'FloatField':        'double precision',
    'ImageField':        'varchar(%(max_length)s)',
    'IntegerField':      'integer',
    'IPAddressField':    'inet',
    'NullBooleanField':  'boolean',
    'OneToOneField':     'integer',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'integer CHECK ("%(column)s" >= 0)',
    'PositiveSmallIntegerField': 'smallint CHECK ("%(column)s" >= 0)',
    'SlugField':         'varchar(%(max_length)s)',
    'SmallIntegerField': 'smallint',
    'TextField':         'text',
    'TimeField':         'time',
    'USStateField':      'varchar(2)',
}
