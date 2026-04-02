HIGH_RISK = [
    'kupoteza fahamu',
    'damu nyingi',
    'maumivu makali sana',
    'kushindwa kupumua',
    'kifua kubana',
]

MEDIUM_RISK = [
    'homa',
    'kutapika',
    'kizunguzungu',
    'maumivu makali',
]


def calculate_risk(question):
    text = (question or '').lower()
    risk = 0

    for word in HIGH_RISK:
        if word in text:
            risk += 3

    for word in MEDIUM_RISK:
        if word in text:
            risk += 1

    if risk >= 3:
        return 'HIGH'
    if risk >= 1:
        return 'MEDIUM'
    return 'LOW'
