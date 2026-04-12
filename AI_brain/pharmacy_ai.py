from inventory.models import MedicineTemplate, PharmacyStock
from decimal import Decimal
from django.db.models import F

def check_drug_interactions(cart_items):
    """Checks for basic duplicate therapy or known interaction categories."""
    interactions = []
    # Extract generic names for comparison
    meds = [item.stock.medicine for item in cart_items]
    
    for i, item1 in enumerate(cart_items):
        for item2 in cart_items[i+1:]:
            # Duplicate category warning (e.g., two antibiotics)
            if 'antibiotic' in item1.medicine.category.lower() and 'antibiotic' in item2.medicine.category.lower():
                interactions.append(f"Warning: {item1.medicine.generic_name} and {item2.medicine.generic_name} are both antibiotics.")
            
            # Add more category-based logic here
    return interactions

def suggest_cheaper_generics(medicine):
    # Suggest cheaper generics for a given medicine
    generics = MedicineTemplate.objects.filter(generic_name=medicine.generic_name).exclude(brand=medicine.brand)
    cheaper = generics.order_by('pharmacy_stocks__price').first()
    if cheaper:
        return [cheaper]
    return []

def predict_demand(pharmacy_id):
    """
    Suggests medicines that are high priority for reorder.
    In production, this would integrate with a time-series model (e.g., Prophet or LSTM).
    """
    # Priority: Items below threshold AND items expiring within 60 days
    low_stock = PharmacyStock.objects.filter(pharmacy_id=pharmacy_id, quantity__lte=F('low_stock_threshold'))
    return [s.medicine for s in low_stock]