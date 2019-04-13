from django.db import migrations


def insert_data(apps, schema_editor):
    Child = apps.get_model('migrations', 'Child')
    Child.objects.create(name='alpha', age=10)
    Child.objects.create(name='bravo', age=20)
    Child.objects.create(name='charlie', age=30)
    Child.objects.create(name='delta', age=40)


class Migration(migrations.Migration):

    dependencies = [('migrations', '0001_initial')]

    operations = [migrations.RunPython(insert_data, migrations.RunPython.noop)]
