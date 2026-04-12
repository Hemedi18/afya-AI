from django import forms
from .models import PubertyProfile, PubertyAnswer

class PubertyProfileForm(forms.ModelForm):
    class Meta:
        model = PubertyProfile
        fields = ["gender", "age", "country", "concerns"]
        widgets = {
            "gender": forms.Select(attrs={"class": "form-select"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": 8, "max": 25}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "concerns": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "List your concerns, separated by commas"}),
        }

class PubertyAssessmentForm(forms.Form):
    age = forms.IntegerField(min_value=8, max_value=25, widget=forms.NumberInput(attrs={"class": "form-control"}))
    gender = forms.ChoiceField(choices=PubertyProfile.GENDER_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    changes_noticed = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Describe changes you have noticed"}))
    mood = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "How do you feel?"}))
    physical_changes = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Describe any physical changes"}))

class PubertyChatForm(forms.Form):
    question = forms.CharField(label="Ask a question", widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Type your puberty question..."}))

class PubertyAnswerForm(forms.ModelForm):
    class Meta:
        model = PubertyAnswer
        fields = ["answer"]
        widgets = {
            "answer": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Your answer..."}),
        }
from .models import PubertyProfile, PubertyAnswer

class PubertyProfileForm(forms.ModelForm):
    class Meta:
        model = PubertyProfile
        fields = ['gender', 'age', 'country', 'concerns']
        widgets = {
            'concerns': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Describe your concerns...'}),
        }

class PubertyAssessmentForm(forms.Form):
    age = forms.IntegerField(min_value=7, max_value=25, label="Your Age")
    gender = forms.ChoiceField(choices=PubertyProfile.GENDER_CHOICES, label="Gender")
    changes_noticed = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), label="What changes have you noticed?")
    mood = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), label="How do you feel emotionally?")
    physical_changes = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), label="Describe any physical changes")

class PubertyAnswerForm(forms.ModelForm):
    class Meta:
        model = PubertyAnswer
        fields = ['answer']
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Your answer...'}),
        }
