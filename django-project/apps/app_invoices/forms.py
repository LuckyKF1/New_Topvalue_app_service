# coding=utf-8
from django import forms
from .models import InvoiceModel


class InvoiceModelForm(forms.ModelForm):
    class Meta:
        model = InvoiceModel
        fields = ['issue_date', 'due_date', 'status', 'invoice_signatured', 'customer_payment']
        exclude = ['invoice_id', 'quotation', 'created_by']

    def __init__(self, *args, **kwargs):
        super(InvoiceModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control w3-input w3-border w3-round-large w3-margin-bottom'
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(attrs={
                    'class':'form-control w3-input w3-border w3-round-large w3-margin-bottom',
                    'type':'date'
                })