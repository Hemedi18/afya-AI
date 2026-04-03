# Compatibility shim to avoid migration-graph conflicts.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('menstrual', '0012_community_media_items'),
    ]

    operations = []
