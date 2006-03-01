"Daily cleanup file"

from django.db import backend, connection, transaction

DOCUMENTATION_DIRECTORY = '/home/html/documentation/'

def clean_up():
    # Clean up old database records
    cursor = connection.cursor()
    cursor.execute("DELETE FROM %s WHERE %s < NOW()" % \
        (backend.quote_name('core_sessions'), backend.quote_name('expire_date')))
    cursor.execute("DELETE FROM %s WHERE %s < NOW() - INTERVAL '1 week'" % \
        (backend.quote_name('registration_challenges'), backend.quote_name('request_date')))
    transaction.commit_unless_managed()

if __name__ == "__main__":
    clean_up()
