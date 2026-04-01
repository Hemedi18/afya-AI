from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .permissions import DOCTOR_GROUP, MODERATOR_GROUP


@receiver(post_migrate)
def ensure_role_groups(sender, **kwargs):
    Group.objects.get_or_create(name=DOCTOR_GROUP)
    Group.objects.get_or_create(name=MODERATOR_GROUP)
