# Generated manually for patient log system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0002_doctor_social'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('frequency', models.CharField(blank=True, help_text='Mfano: Mara 2 kwa siku, Kila asubuhi baada ya chakula', max_length=120)),
                ('is_active', models.BooleanField(default=True)),
                ('is_sent', models.BooleanField(default=False, help_text='Imekuwa sent kwa patient au bado')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_patient_logs', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_patient_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PatientLogField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_label', models.CharField(max_length=200)),
                ('field_type', models.CharField(choices=[('text', 'Maandishi mafupi'), ('textarea', 'Maandishi marefu'), ('number', 'Namba'), ('select', 'Chaguo (dropdown)'), ('checkbox', 'Ndio/Hapana'), ('scale', 'Kiwango 1–10')], default='text', max_length=20)),
                ('placeholder', models.CharField(blank=True, max_length=250)),
                ('options', models.JSONField(blank=True, default=list)),
                ('required', models.BooleanField(default=False)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='doctor.patientlog')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='PatientLogEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(default=dict)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='doctor.patientlog')),
                ('submitted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='log_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
    ]
