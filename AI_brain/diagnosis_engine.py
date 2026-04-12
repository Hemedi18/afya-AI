def get_growth_risk_advice(name, gender, birth_date, data):
    """
    Provide basic growth risk advice based on weight/height trends.
    This is a placeholder for future AI integration.
    """
    if not data or len(data) < 2:
        return "Not enough data for risk analysis."
    last = data[-1]
    prev = data[-2]
    alerts = []
    if last['weight'] < prev['weight']:
        alerts.append("Weight loss detected. Possible malnutrition risk.")
    if last['height'] < prev['height']:
        alerts.append("Height decrease detected. Possible stunting.")
    if last['weight'] > prev['weight'] * 1.2:
        alerts.append("Rapid weight gain. Monitor for obesity.")
    if not alerts:
        return "Growth appears normal. Continue regular monitoring."
    return " ".join(alerts)
from .medical_dataset import MEDICAL_DATASET


def get_possible_conditions(symptom):
    if symptom in MEDICAL_DATASET:
        return MEDICAL_DATASET[symptom].get('possible_conditions', [])
    return []


def get_red_flags(symptom):
    if symptom in MEDICAL_DATASET:
        return MEDICAL_DATASET[symptom].get('red_flags', [])
    return []

# Basic puberty advice function for integration with puberty app
def get_puberty_advice(question, user=None):
    """
    Provide basic puberty advice based on keywords in the question.
    This is a placeholder for future AI integration.
    """
    q = question.lower()
    if any(word in q for word in ['period', 'menstruation', 'menstrual']):
        return "Menstruation is a normal part of puberty. Maintain good hygiene, track your cycle, and consult a doctor if you have severe pain or irregularities."
    if any(word in q for word in ['growth', 'height', 'tall', 'short']):
        return "Growth spurts are common during puberty. Eat a balanced diet, exercise, and get enough sleep."
    if any(word in q for word in ['acne', 'pimples', 'skin']):
        return "Acne is common in puberty. Wash your face regularly and avoid oily foods. If severe, consult a dermatologist."
    if any(word in q for word in ['voice', 'deep', 'change']):
        return "Voice changes are normal during puberty, especially for boys. This is due to hormonal changes."
    if any(word in q for word in ['breast', 'chest']):
        return "Breast development is a normal part of puberty for girls. If you have concerns, talk to a trusted adult or doctor."
    if any(word in q for word in ['hair', 'armpit', 'pubic']):
        return "Hair growth in new areas is normal during puberty. Maintain good hygiene."
    if any(word in q for word in ['emotion', 'mood', 'feel']):
        return "Mood swings are common due to hormonal changes. Talk to someone you trust if you feel overwhelmed."
    return "Puberty brings many changes. If you have specific concerns, please ask or consult a health professional."
