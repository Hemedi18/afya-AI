from django import forms
from .models import Child, GrowthRecord, ChildMilestone, ChildVaccination

class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ["name", "gender", "birth_date", "birth_weight", "birth_height", "blood_group"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "birth_weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "birth_height": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "blood_group": forms.Select(attrs={"class": "form-select"}),
        }

class GrowthRecordForm(forms.ModelForm):
    class Meta:
        model = GrowthRecord
        fields = ["weight", "height", "head_circumference", "recorded_at"]
        widgets = {
            "weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "height": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "head_circumference": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "recorded_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

class ChildMilestoneForm(forms.ModelForm):
    class Meta:
        model = ChildMilestone
        fields = ["milestone", "achieved", "achieved_date"]
        widgets = {
            "milestone": forms.Select(attrs={"class": "form-select"}),
            "achieved": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "achieved_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

class ChildVaccinationForm(forms.ModelForm):
    class Meta:
        model = ChildVaccination
        fields = ["vaccination", "completed", "completed_date"]
        widgets = {
            "vaccination": forms.Select(attrs={"class": "form-select"}),
            "completed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "completed_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
