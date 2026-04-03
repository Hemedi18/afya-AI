from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0004_patientlog_metadata_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientlogentry',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
