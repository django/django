"Daily cleanup file"

from django.core.db import db

DOCUMENTATION_DIRECTORY = '/home/html/documentation/'

def clean_up():
    # Clean up old database records
    cursor = db.cursor()
    cursor.execute("DELETE FROM %s WHERE %s < NOW()" % \
        (db.quote_name('core_sessions'), db.quote_name('expire_date')))
    cursor.execute("DELETE FROM %s WHERE %s < NOW() - INTERVAL '1 week'" % \
        (db.quote_name('registration_challenges'), db.quote_name('request_date')))
    db.commit()

if __name__ == "__main__":
    clean_up()
