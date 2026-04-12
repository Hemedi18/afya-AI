from django import forms
from django.utils.translation import gettext_lazy as _

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        label=_("Shipping Address / Location"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your delivery address or coordinates')
        }),
        help_text=_("Format: Street, City or Lat,Lon")
    )
    prescription_file = forms.FileField(
        label=_("Attach Prescription"),
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        requires_prescription = kwargs.pop('requires_prescription', False)
        super().__init__(*args, **kwargs)
        if requires_prescription:
            self.fields['prescription_file'].required = True
            self.fields['prescription_file'].help_text = _("One or more items in your cart require a verified prescription.")