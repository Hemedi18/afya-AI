from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0003_patient_logs'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientlog',
            name='metadata_fields',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Metadata zilizoruhusiwa na daktari kwa analysis, mfano ["entry_time","patient_region"]',
            ),
        ),
    ]
