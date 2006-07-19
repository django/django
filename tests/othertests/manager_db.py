from django.db import models

def run_tests(verbosity=0):
    class Insect(models.Model):
        common_name = models.CharField(maxlength=64)
        latin_name = models.CharField(maxlength=128)

        class Meta:
            app_label = 'manager_db'

    m = Insect.objects
    db = Insect.objects.db

    assert db
    assert db.connection
    assert db.connection.cursor
    assert db.backend
    assert db.backend.quote_name
    assert db.get_creation_module

if __name__ == '__main__':
    run_tests()
    print "ok"
