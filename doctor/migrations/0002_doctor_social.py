from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0002_doctor_rating_report'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('menstrual', '0012_community_media_items'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoctorFollow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('doctor_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to='menstrual.doctorprofile')),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followed_doctors', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('follower', 'doctor_profile')},
            },
        ),
    ]
