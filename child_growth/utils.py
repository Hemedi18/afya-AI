from datetime import date

# Example: Calculate age in months
def age_in_months(birth_date):
    today = date.today()
    return (today.year - birth_date.year) * 12 + today.month - birth_date.month

# Example: Generate data for Chart.js
def growth_chart_data(records):
    """
    Returns dict with labels (dates), weights, heights for Chart.js
    """
    labels = [r.recorded_at.strftime('%Y-%m-%d') for r in records]
    weights = [r.weight for r in records]
    heights = [r.height for r in records]
    return {
        'labels': labels,
        'weights': weights,
        'heights': heights,
    }

# Example: Simple percentile/risk logic (placeholder for real WHO data)
def simple_growth_risk(weight, height, age_months):
    # This is a placeholder. In production, use WHO/CDC growth charts.
    if age_months < 24:
        if weight < 6:
            return 'Underweight'
        elif weight > 14:
            return 'Obese'
    else:
        if weight < 12:
            return 'Underweight'
        elif weight > 25:
            return 'Obese'
    return 'Normal'

# Example: Get due vaccinations
def get_due_vaccinations(child, all_vaccines, completed_vaccines):
    due = [v for v in all_vaccines if v not in completed_vaccines]
    return due
