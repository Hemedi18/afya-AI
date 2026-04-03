# Generated manually for multi-media support on posts/statuses
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('menstrual', '0011_communitygroup_image_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityPostMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], max_length=10)),
                ('image', models.ImageField(blank=True, null=True, upload_to='community_posts/multi/')),
                ('video', models.FileField(blank=True, null=True, upload_to='community_posts/videos/multi/')),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='menstrual.communitypost')),
            ],
            options={
                'ordering': ['sort_order', 'created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='CommunityStatusMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], max_length=10)),
                ('image', models.ImageField(blank=True, null=True, upload_to='community_status/multi/')),
                ('video', models.FileField(blank=True, null=True, upload_to='community_status/videos/multi/')),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='menstrual.communitystatus')),
            ],
            options={
                'ordering': ['sort_order', 'created_at', 'id'],
            },
        ),
    ]
