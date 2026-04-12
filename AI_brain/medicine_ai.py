from inventory.models import MedicineTemplate, PharmacyStock
from django.db.models import Q

def suggest_medicines(symptoms, limit=5):
    # Placeholder: Suggest medicines based on symptoms (to be replaced with ML logic)
    return MedicineTemplate.objects.filter(description__icontains=symptoms).order_by('?')[:limit]

def alternative_medicines(medicine_id, limit=3):
    try:
        medicine = MedicineTemplate.objects.get(pk=medicine_id)
        return MedicineTemplate.objects.filter(category=medicine.category).exclude(pk=medicine_id)[:limit]
    except MedicineTemplate.DoesNotExist:
        return MedicineTemplate.objects.none()

def cheaper_options(medicine_id, limit=3):
    try:
        medicine = MedicineTemplate.objects.get(pk=medicine_id)
        stocks = PharmacyStock.objects.filter(medicine=medicine).order_by('price')[:limit]
        return stocks
    except MedicineTemplate.DoesNotExist:
        return PharmacyStock.objects.none()

def risk_alerts(user, medicine_id):
    # Placeholder: Implement risk alert logic (e.g., allergies, interactions)
    return []
