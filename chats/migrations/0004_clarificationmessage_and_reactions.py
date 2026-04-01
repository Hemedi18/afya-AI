from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0003_clarificationrequest_target_doctor'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='clarificationrequest',
            name='dislikes',
            field=models.ManyToManyField(blank=True, related_name='clarification_dislikes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='clarificationrequest',
            name='likes',
            field=models.ManyToManyField(blank=True, related_name='clarification_likes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='ClarificationMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('clarification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chats.clarificationrequest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clarification_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
