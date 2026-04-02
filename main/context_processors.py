import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from AI_brain.models import AIInteractionLog
from AI_brain.services import generate_ai_text
from menstrual.models import CommunityPost, DailyLog, DoctorProfile, Reminder


def _series_by_day(queryset, date_field, days=14):
    today = timezone.now().date()
    start = today - timezone.timedelta(days=days - 1)

    model_field = queryset.model._meta.get_field(date_field)
    if model_field.get_internal_type() == 'DateField':
        lookup = f'{date_field}__gte'
    else:
        lookup = f'{date_field}__date__gte'

    rows = (
        queryset.filter(**{lookup: start})
        .annotate(day=TruncDate(date_field))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )
    mapped = {row['day']: row['total'] for row in rows}
    labels, values = [], []
    for i in range(days):
        d = start + timezone.timedelta(days=i)
        labels.append(d.strftime('%d %b'))
        values.append(int(mapped.get(d, 0)))
    return labels, values


def _safe_feedback_rating(log):
    payload = log.context_payload or {}
    feedback = payload.get('feedback') or {}
    if isinstance(feedback, dict):
        return (feedback.get('rating') or '').strip().lower()
    return ''


def _simple_series_summary(title, labels, values):
    if not values:
        return f'{title}: hakuna data ya kutosha.'
    total = sum(values)
    peak = max(values)
    peak_idx = values.index(peak)
    return f'{title}: jumla {total}, kilele {peak} ({labels[peak_idx]}), ya mwisho {values[-1]}.'


def _ai_summary(payload):
    fallback = (
        'AI summary haijapatikana sasa. Angalia trend za registration, posting, '
        'content types, feedback, na notifications kwa hatua za haraka.'
    )
    prompt = (
        'You are an admin analytics assistant. Summarize in concise Swahili. '
        'Give quick actionable insights under 6 short bullet points.\n\n'
        f"Analytics payload: {payload}"
    )
    return generate_ai_text(prompt, fallback)


def admin_dashboard_context(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated or not request.user.is_staff:
        return {}

    path = (request.path or '').lower()
    if '/admin' not in path:
        return {}

    cache_key = 'admin_dashboard_context_v1'
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.now()
    start_30d = now - timezone.timedelta(days=30)

    reg_labels, reg_values = _series_by_day(User.objects.all(), 'date_joined', days=14)
    post_labels, post_values = _series_by_day(CommunityPost.objects.all(), 'created_at', days=14)
    log_labels, log_values = _series_by_day(DailyLog.objects.all(), 'date', days=14)
    ai_labels, ai_values = _series_by_day(AIInteractionLog.objects.exclude(question='[USER_FEEDBACK]'), 'created_at', days=14)

    posts_30 = CommunityPost.objects.filter(created_at__gte=start_30d)
    text_only_posts = posts_30.filter(Q(image__isnull=True) | Q(image=''), Q(video__isnull=True) | Q(video='')).count()
    image_posts = posts_30.filter(Q(image__isnull=False) & ~Q(image='')).count()
    video_posts = posts_30.filter(Q(video__isnull=False) & ~Q(video='')).count()

    feedback_qs = AIInteractionLog.objects.filter(created_at__gte=start_30d, question='[USER_FEEDBACK]')
    helpful = 0
    not_helpful = 0
    for row in feedback_qs:
        rating = _safe_feedback_rating(row)
        if rating == 'up':
            helpful += 1
        elif rating == 'down':
            not_helpful += 1

    feedback_total = helpful + not_helpful
    helpful_rate = round((helpful / feedback_total) * 100, 1) if feedback_total else 0

    notifications = {
        'pending_reminders': Reminder.objects.filter(is_notified=False).count(),
        'unverified_doctors': DoctorProfile.objects.filter(verified=False).count(),
        'negative_feedback_30d': not_helpful,
    }

    suggestions = []
    if not_helpful > helpful:
        suggestions.append('Boresha prompt templates za AI na ongeza clarification questions kabla ya final advice.')
    if notifications['pending_reminders'] > 30:
        suggestions.append('Punguza backlog ya reminders; hakikisha scheduler inafanya kazi kila siku.')
    if notifications['unverified_doctors'] > 0:
        suggestions.append('Kagua doctor applications zilizosubiri ili kuboresha service trust.')
    if not suggestions:
        suggestions.append('Trend zinaonekana stable. Endelea kufuatilia growth na quality wiki hii.')

    ai_payload = {
        'users_total': User.objects.count(),
        'registrations_14d': reg_values,
        'posts_14d': post_values,
        'ai_chats_14d': ai_values,
        'daily_logs_14d': log_values,
        'content_types_30d': {
            'text': text_only_posts,
            'image': image_posts,
            'video': video_posts,
        },
        'feedback_30d': {
            'helpful': helpful,
            'not_helpful': not_helpful,
            'helpful_rate': helpful_rate,
        },
        'notifications': notifications,
    }

    context = {
        'admin_dash': {
            'kpis': {
                'users': User.objects.count(),
                'posts_30d': posts_30.count(),
                'daily_logs_30d': DailyLog.objects.filter(date__gte=start_30d.date()).count(),
                'ai_chats_30d': AIInteractionLog.objects.filter(created_at__gte=start_30d).exclude(question='[USER_FEEDBACK]').count(),
                'helpful_rate': helpful_rate,
            },
            'charts': {
                'reg_labels': json.dumps(reg_labels),
                'reg_values': reg_values,
                'post_labels': json.dumps(post_labels),
                'post_values': post_values,
                'log_labels': json.dumps(log_labels),
                'log_values': log_values,
                'ai_labels': json.dumps(ai_labels),
                'ai_values': ai_values,
                'content_labels': json.dumps(['Text', 'Image', 'Video']),
                'content_values': [text_only_posts, image_posts, video_posts],
                'feedback_labels': json.dumps(['Helpful', 'Not Helpful']),
                'feedback_values': [helpful, not_helpful],
            },
            'summaries': {
                'reg': _simple_series_summary('Registration 14d', reg_labels, reg_values),
                'post': _simple_series_summary('Posting 14d', post_labels, post_values),
                'log': _simple_series_summary('Daily logs 14d', log_labels, log_values),
                'ai': _simple_series_summary('AI usage 14d', ai_labels, ai_values),
            },
            'notifications': notifications,
            'suggestions': suggestions,
            'ai_summary': _ai_summary(ai_payload),
        }
    }

    cache.set(cache_key, context, 300)
    return context
