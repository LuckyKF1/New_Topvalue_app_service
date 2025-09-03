# coding=utf-8
from django import forms
from django.forms import ModelForm

# Models
from .models import ContractsModel


# ModelForm Here
class ContractsModelForm(forms.ModelForm):
    class Meta:
        model = ContractsModel
        fields = '__all__'
        widgets = {
            'start_contract':forms.DateInput(attrs={type:'date'}),
            'end_contract':forms.DateInput(attrs={type:'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control w3-input w3-border w3-round-large w3-margin-bottom'

            if field_name in ['contract_id', 'status']:
                field.widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        start_contract = cleaned_data.get('start_contract')
        end_contract = cleaned_data.get('end_contract')

        if start_contract and end_contract and end_contract <= start_contract:
            self.add_error('end_contract', 'End Date must be after start date')
        
        return cleaned_data