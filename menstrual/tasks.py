import logging
import re
from html import unescape
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Max, Q
from groq import Groq
from AI_brain.services import generate_ai_text
from .models import DailyLog, MenstrualCycle, Reminder, MenstrualUserSetting, DailyTip

logger = logging.getLogger(__name__)


TRUSTED_TIP_SOURCES = [
    {
        'title': 'Fahamu kinachoonekana kawaida kwenye period',
        'url': 'https://www.nhs.uk/conditions/periods/',
        'publisher': 'NHS',
        'topic': 'period basics, normal cycle, heavy flow, product safety',
    },
    {
        'title': 'Njia salama za kupunguza period pain',
        'url': 'https://www.nhs.uk/conditions/period-pain/',
        'publisher': 'NHS',
        'topic': 'period pain relief, when to seek medical help, warm bath, gentle exercise',
    },
    {
        'title': 'Dalili za kawaida za hedhi na lini uwasiliane na daktari',
        'url': 'https://medlineplus.gov/menstruation.html',
        'publisher': 'MedlinePlus',
        'topic': 'menstruation basics, cramps, bloating, mood changes, warning signs',
    },
    {
        'title': 'Track mzunguko wako ili kugundua mabadiliko mapema',
        'url': 'https://www.mayoclinic.org/healthy-lifestyle/womens-health/in-depth/menstrual-cycle/art-20047186',
        'publisher': 'Mayo Clinic',
        'topic': 'cycle tracking, normal cycle length, irregular periods, warning signs',
    },
    {
        'title': 'Usafi wa hedhi na matumizi salama ya products',
        'url': 'https://www.cdc.gov/hygiene/about/menstrual-hygiene.html',
        'publisher': 'CDC',
        'topic': 'menstrual hygiene, changing pads/tampons, infection prevention, safety',
    },
]


def _download_web_text(url, timeout=8):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 ZanzHubHealthBot/1.0'})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='ignore')


def _clean_html_to_text(html):
    html = re.sub(r'(?is)<(script|style|noscript).*?>.*?</\1>', ' ', html)
    html = re.sub(r'(?is)<svg.*?>.*?</svg>', ' ', html)
    html = re.sub(r'(?s)<[^>]+>', ' ', html)
    text = unescape(html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_relevant_summary(raw_text, topic):
    keywords = [
        'period', 'menstrual', 'cycle', 'pain', 'cramp', 'bleeding', 'ovulation',
        'hygiene', 'tampon', 'pad', 'flow', 'fertility', 'symptom', 'doctor'
    ]
    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    relevant = []
    for sentence in sentences:
        lowered = sentence.lower()
        if 35 <= len(sentence) <= 280 and any(word in lowered for word in keywords):
            if 'cookies' in lowered or 'advertisement' in lowered or 'skip to' in lowered:
                continue
            relevant.append(sentence.strip())
        if len(relevant) >= 4:
            break

    if not relevant:
        relevant = [topic]
    return ' '.join(relevant[:3])


def _tip_ui_structure(index):
    palettes = [
        {'accent': '#c9184a', 'accent_soft': 'rgba(201,24,74,0.12)', 'glow': 'rgba(201,24,74,0.20)'},
        {'accent': '#7c3aed', 'accent_soft': 'rgba(124,58,237,0.14)', 'glow': 'rgba(124,58,237,0.22)'},
        {'accent': '#0f766e', 'accent_soft': 'rgba(15,118,110,0.14)', 'glow': 'rgba(15,118,110,0.22)'},
        {'accent': '#ea580c', 'accent_soft': 'rgba(234,88,12,0.14)', 'glow': 'rgba(234,88,12,0.22)'},
        {'accent': '#2563eb', 'accent_soft': 'rgba(37,99,235,0.14)', 'glow': 'rgba(37,99,235,0.22)'},
    ]
    return palettes[index % len(palettes)]


def refresh_daily_tips_task(limit=5, force=False):
    today = timezone.localdate()
    existing_today = DailyTip.objects.filter(date_created=today).count()
    if existing_today >= limit and not force:
        return existing_today

    created = 0
    trusted_sources = TRUSTED_TIP_SOURCES[:limit]

    for index, source in enumerate(trusted_sources):
        if DailyTip.objects.filter(date_created=today, title=source['title']).exists() and not force:
            continue

        try:
            html = _download_web_text(source['url'])
            cleaned = _clean_html_to_text(html)
            summary_seed = _extract_relevant_summary(cleaned, source['topic'])
        except (URLError, TimeoutError, ValueError, OSError, ET.ParseError) as exc:
            logger.warning('Tip fetch failed for %s: %s', source['url'], exc)
            summary_seed = source['topic']

        prompt = (
            'Tengeneza daily tip moja ya afya ya hedhi kwa Kiswahili rahisi na salama kitabibu. '
            f'Chanzo ni {source["publisher"]}. '
            f'Muhtasari wa chanzo: {summary_seed}. '
            'Jibu sentensi 2 fupi tu, zenye hatua ya kujitunza na onyo la kwenda hospitali kama dalili ni kali.'
        )
        fallback = f"{summary_seed[:240]} Endapo maumivu, bleeding nyingi au mabadiliko makubwa ya mzunguko yanaendelea, zungumza na daktari."
        content = generate_ai_text(prompt, fallback)

        if force:
            DailyTip.objects.filter(date_created=today, title=source['title']).delete()

        DailyTip.objects.create(
            title=source['title'],
            content=content,
            source='WEB',
            url=source['url'],
            ui_structure=_tip_ui_structure(index),
        )
        created += 1

    return DailyTip.objects.filter(date_created=today).count() or created

def generate_log_insight_task(log_id):
    """
    Background task to generate AI insights based on the daily log entry.
    Triggered via django-q in menstrual/models.py.
    """
    try:
        log = DailyLog.objects.get(id=log_id)
        if not settings.GROQ_API_KEY:
            return

        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Constructing a Swahili-centric prompt for the AI assistant
        symptoms_str = ', '.join(log.physical_symptoms) if log.physical_symptoms else 'Hakuna'
        
        prompt = (
            f"Wewe ni msaidizi wa afya ya uzazi. Mtumiaji ameweka taarifa zifuatazo:\n"
            f"- Kiwango cha damu: {log.flow_intensity}/5\n"
            f"- Dalili: {symptoms_str}\n"
            f"Toa ushauri mmoja mfupi wa afya na faraja kwa Kiswahili."
        )

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )

        log.ai_suggestion = completion.choices[0].message.content
        log.save(update_fields=['ai_suggestion'])
    except Exception as e:
        logger.error(f"AI Task Error for log_id {log_id}: {str(e)}", exc_info=True)

def check_upcoming_periods_task():
    """
    Scheduled task to run daily. Checks for upcoming periods 
    and creates reminders for users.
    """
    today = timezone.now().date()
    active_cycles = MenstrualCycle.objects.filter(is_active=True)

    for cycle in active_cycles:
        settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=cycle.user)
        next_period = cycle.start_date + timedelta(days=cycle.cycle_length)
        ovulation_day = next_period - timedelta(days=14)
        fertile_start = ovulation_day - timedelta(days=5)

        # Period reminder (2 days before)
        if settings_obj.reminder_period and next_period - today == timedelta(days=2):
            Reminder.objects.get_or_create(
                user=cycle.user,
                event_date=next_period,
                defaults={'title': "Kikumbusho: Kipindi chako kinatarajiwa kuanza baada ya siku 2."},
            )

        # Ovulation reminder (same day)
        if settings_obj.reminder_ovulation and ovulation_day == today:
            Reminder.objects.get_or_create(
                user=cycle.user,
                event_date=ovulation_day,
                defaults={'title': "Ovulation alert: Leo ni siku yako ya ovulation kwa makadirio."},
            )

        # Fertile window start reminder
        if settings_obj.reminder_fertile_window and fertile_start == today:
            Reminder.objects.get_or_create(
                user=cycle.user,
                event_date=fertile_start,
                defaults={'title': "Fertile window imeanza leo kwa makadirio ya AI."},
            )

        # Safety reminder if period seems overdue by more than 7 days
        if settings_obj.emergency_alerts_enabled and today > (next_period + timedelta(days=7)):
            Reminder.objects.get_or_create(
                user=cycle.user,
                event_date=today,
                defaults={
                    'title': "Tahadhari: Kipindi kimechelewa zaidi ya siku 7. Inashauriwa kuwasiliana na daktari."
                }
            )

def close_inactive_cycles_task():
    """
    Finds active cycles with no logs for 40 days (or no logs at all
    since starting 40 days ago) and marks them as inactive.
    """
    today = timezone.now().date()
    threshold_date = today - timedelta(days=40)

    # Query for cycles where:
    # 1. The latest log date is older than 40 days OR
    # 2. There are no logs and the start_date is older than 40 days
    MenstrualCycle.objects.annotate(
        last_activity=Max('daily_logs__date')
    ).filter(
        is_active=True
    ).filter(
        Q(last_activity__lt=threshold_date) | 
        Q(last_activity__isnull=True, start_date__lt=threshold_date)
    ).update(is_active=False)