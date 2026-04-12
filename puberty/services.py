from AI_brain.diagnosis_engine import get_puberty_advice
from AI_brain.medicine_ai import suggest_medicines
from inventory.models import MedicineTemplate
from django.utils import timezone

def ai_puberty_response(question, user=None):
    """
    Integrate with AI_brain for puberty Q&A.
    """
    try:
        return get_puberty_advice(question, user=user)
    except Exception:
        if 'hygiene' in question.lower():
            return suggest_medicines('hygiene')
        return "Sorry, I couldn't find an answer. Please consult a health professional."

def assess_puberty_stage(age, gender, changes_noticed, mood, physical_changes):
    """
    Simple logic to estimate puberty stage based on age and changes.
    """
    stage = "Early"
    if age >= 14 and ("voice" in changes_noticed.lower() or "menstruation" in changes_noticed.lower() or "breast" in changes_noticed.lower()):
        stage = "Mid"
    if age >= 16 and ("facial hair" in physical_changes.lower() or "period" in changes_noticed.lower()):
        stage = "Late"
    return stage

def recommend_hygiene_products(gender):
    """
    Recommend hygiene products from pharmacy based on gender.
    """
    if gender == "female":
        return MedicineTemplate.objects.filter(category__icontains="sanitary")[:3]
    return MedicineTemplate.objects.filter(category__icontains="hygiene")[:3]
