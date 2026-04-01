from django import forms


class OfflineChatInputForm(forms.Form):
    message = forms.CharField(
        max_length=3000,
        widget=forms.Textarea(
            attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Andika ujumbe wako hapa...',
            }
        ),
    )
