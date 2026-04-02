EMERGENCY_SIGNS = [
    'kupoteza fahamu',
    'kushindwa kupumua',
    'damu nyingi',
    'maumivu makali sana',
    'kifua kubana',
    'degedege',
    'kupooza',
]

URGENT_SIGNS = [
    'homa kali',
    'kutapika sana',
    'maumivu makali',
    'kizunguzungu',
]


def triage_level(text):
    t = (text or '').lower()

    for sign in EMERGENCY_SIGNS:
        if sign in t:
            return 'EMERGENCY'

    for sign in URGENT_SIGNS:
        if sign in t:
            return 'URGENT'

    return 'NORMAL'
