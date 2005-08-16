"Daily cleanup file"

from django.core.db import db

DOCUMENTATION_DIRECTORY = '/home/html/documentation/'

def clean_up():
    # Clean up old database records
    cursor = db.cursor()
    cursor.execute("DELETE FROM core_sessions WHERE expire_date < NOW()")
    cursor.execute("DELETE FROM registration_challenges WHERE request_date < NOW() - INTERVAL '1 week'")
    db.commit()

if __name__ == "__main__":
    clean_up()
