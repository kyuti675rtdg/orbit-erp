from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "industry", "country", "city", "phone", "email", "tin", "address", "plan"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Heleph Coffee Group"}),
            "industry": forms.TextInput(attrs={"placeholder": "e.g. Coffee Export & Logistics"}),
            "city": forms.TextInput(attrs={"placeholder": "e.g. Addis Ababa"}),
            "phone": forms.TextInput(attrs={"placeholder": "+251 ..."}),
            "email": forms.EmailInput(attrs={"placeholder": "info@company.et"}),
            "address": forms.TextInput(attrs={"placeholder": "Street / Woreda / Sub-city"}),
        }
