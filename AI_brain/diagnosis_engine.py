from .medical_dataset import MEDICAL_DATASET


def get_possible_conditions(symptom):
    if symptom in MEDICAL_DATASET:
        return MEDICAL_DATASET[symptom].get('possible_conditions', [])
    return []


def get_red_flags(symptom):
    if symptom in MEDICAL_DATASET:
        return MEDICAL_DATASET[symptom].get('red_flags', [])
    return []
