from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0005_patientlogentry_metadata'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('menstrual', '0012_community_media_items'),
    ]

    operations = [
        migrations.RenameField(
            model_name='doctorrating',
            old_name='user',
            new_name='rater',
        ),
        migrations.RenameField(
            model_name='doctorrating',
            old_name='doctor',
            new_name='doctor_profile',
        ),
        migrations.RenameField(
            model_name='doctorrating',
            old_name='rating',
            new_name='score',
        ),
        migrations.RenameField(
            model_name='doctorrating',
            old_name='comment',
            new_name='note',
        ),
        migrations.AlterField(
            model_name='doctorrating',
            name='rater',
            field=models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='doctor_ratings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='doctorrating',
            name='doctor_profile',
            field=models.ForeignKey(db_column='doctor_id', on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='menstrual.doctorprofile'),
        ),
        migrations.AlterField(
            model_name='doctorrating',
            name='score',
            field=models.PositiveSmallIntegerField(db_column='rating', default=5),
        ),
        migrations.AlterField(
            model_name='doctorrating',
            name='note',
            field=models.TextField(blank=True, db_column='comment'),
        ),
        migrations.AlterField(
            model_name='doctorrating',
            name='date',
            field=models.DateField(db_column='date', default=django.utils.timezone.localdate),
        ),
        migrations.RenameField(
            model_name='doctorreport',
            old_name='user',
            new_name='reporter',
        ),
        migrations.RenameField(
            model_name='doctorreport',
            old_name='doctor',
            new_name='doctor_profile',
        ),
        migrations.AlterField(
            model_name='doctorreport',
            name='reporter',
            field=models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='doctor_reports', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='doctorreport',
            name='doctor_profile',
            field=models.ForeignKey(db_column='doctor_id', on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='menstrual.doctorprofile'),
        ),
    ]
