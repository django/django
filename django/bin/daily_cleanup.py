"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

from django.db import backend, connection, transaction

def clean_up():
    # Clean up old database records
    cursor = connection.cursor()
    cursor.execute("DELETE FROM %s WHERE %s < NOW()" % \
        (backend.quote_name('django_session'), backend.quote_name('expire_date')))
    transaction.commit_unless_managed()

if __name__ == "__main__":
    clean_up()
