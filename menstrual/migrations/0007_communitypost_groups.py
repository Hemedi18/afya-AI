from django.db import migrations, models


def copy_group_to_groups(apps, schema_editor):
    CommunityPost = apps.get_model('menstrual', 'CommunityPost')
    for post in CommunityPost.objects.exclude(group__isnull=True):
        post.groups.add(post.group_id)


class Migration(migrations.Migration):

    dependencies = [
        ('menstrual', '0006_communityreply_dislikes_communityreply_likes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='communitypost',
            name='groups',
            field=models.ManyToManyField(blank=True, related_name='multi_posts', to='menstrual.communitygroup'),
        ),
        migrations.RunPython(copy_group_to_groups, migrations.RunPython.noop),
    ]
