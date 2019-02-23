from django.db import migrations

from ..operations import Operation0


class Migration(migrations.Migration):

    operations = [
        Operation0(),
    ]
