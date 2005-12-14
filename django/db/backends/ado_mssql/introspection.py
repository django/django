def get_table_list(cursor):
    raise NotImplementedError

def get_table_description(cursor, table_name):
    raise NotImplementedError

def get_relations(cursor, table_name):
    raise NotImplementedError

DATA_TYPES_REVERSE = {}
