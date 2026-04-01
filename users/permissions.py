from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


DOCTOR_GROUP = 'Doctor'
MODERATOR_GROUP = 'Moderator'


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def is_doctor(user):
    return bool(user and user.is_authenticated and user.groups.filter(name=DOCTOR_GROUP).exists())


def is_moderator(user):
    return bool(user and user.is_authenticated and user.groups.filter(name=MODERATOR_GROUP).exists())


def can_moderate(user):
    return is_admin(user) or is_moderator(user)


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


class DoctorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user) or is_doctor(self.request.user)


class ModeratorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return can_moderate(self.request.user)