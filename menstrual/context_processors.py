from .models import Reminder

def reminders_processor(request):
    if request.user.is_authenticated:
        unread_reminders = Reminder.objects.filter(user=request.user, is_notified=False).order_by('-event_date')
        return {
            'unread_reminders': unread_reminders,
            'unread_reminders_count': unread_reminders.count()
        }
    return {'unread_reminders': [], 'unread_reminders_count': 0}