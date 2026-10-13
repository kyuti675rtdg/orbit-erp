# Removes the legacy chat models from comms (replaced by Orbit Chat).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comms', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(name='MessageRead'),
        migrations.DeleteModel(name='Message'),
        migrations.DeleteModel(name='Conversation'),
    ]
