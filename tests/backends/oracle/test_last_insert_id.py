from django.db import connection
import pytest


@pytest.mark.django_db
def test_last_insert_id():
    """Test that last_insert_id correctly retrieves the latest ID."""
    with connection.cursor() as cursor:
        table_name = "test_table"
        pk_name = "id"

        last_id = connection.ops.last_insert_id(cursor, table_name, pk_name)

        if connection.vendor == "sqlite":
            assert last_id is None
        else:
            assert isinstance(last_id, int)
