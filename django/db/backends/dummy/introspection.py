from django.db.backends.dummy.base import complain

get_table_list = complain
get_table_description = complain
get_relations = complain
get_indexes = complain
table_exists = complain

DATA_TYPES_REVERSE = {}
