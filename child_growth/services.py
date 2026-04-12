from AI_brain.diagnosis_engine import get_growth_risk_advice
from .models import GrowthRecord, Child
from django.utils import timezone

# AI-powered risk detection and growth analysis

def analyze_growth(child: Child, records=None):
    """
    Analyze growth records for a child and return risk alerts and trends.
    Integrates with AI_brain for malnutrition, stunting, obesity, and delay detection.
    """
    if records is None:
        records = child.growth_records.order_by('recorded_at')
    if not records.exists():
        return {
            'trend': None,
            'alerts': [],
            'ai_advice': None,
        }
    # Prepare data for AI
    data = [
        {
            'date': str(r.recorded_at),
            'weight': r.weight,
            'height': r.height,
            'head_circumference': r.head_circumference,
        } for r in records
    ]
    # Call AI_brain for risk analysis
    try:
        ai_advice = get_growth_risk_advice(child.name, child.gender, child.birth_date, data)
    except Exception:
        ai_advice = None
    # Simple trend: compare last two records
    alerts = []
    if len(data) >= 2:
        last = data[-1]
        prev = data[-2]
        if last['weight'] < prev['weight']:
            alerts.append('Weight loss detected')
        if last['height'] < prev['height']:
            alerts.append('Height decrease detected')
    return {
        'trend': data,
        'alerts': alerts,
        'ai_advice': ai_advice,
    }


def get_nutrition_tips(age_months):
    """
    Return nutrition tips for a given age in months.
    """
    from .models import NutritionTip
    if age_months < 6:
        group = '0-6 months'
    elif age_months < 12:
        group = '6-12 months'
    elif age_months < 60:
        group = '1-5 years'
    else:
        group = '5+ years'
    return NutritionTip.objects.filter(age_group__icontains=group)
