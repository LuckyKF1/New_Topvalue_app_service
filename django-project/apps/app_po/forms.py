# coding=utf-8
from django import forms
from django.forms import inlineformset_factory

# Model 
from .models import PurchaseOrderModel, PurchaseOrderItemsModel, PoIdGeneratorModel

# Purchase Order Information ModelForm
class PurchaseOrderModelForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderModel
        fields = '__all__'
        exclude = ['po_id', 'created_by', 'created_at_log', 'updated_at_log']

    def __init__(self, *args, **kwargs):
        super(PurchaseOrderModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control w3-input w3-border w3-round-large w3-margin-bottom'
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(attrs={
                    'class':'form-control w3-input w3-border w3-round-large w3-margin-bottom',
                    'type':'date'
                })

# Purchase Order Items Model Form
class PurchaseOrderItemsModelForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItemsModel
        readonly_fields = ['product_name', 'qty', 'period']
        fields = ['product_name', 'price', 'qty', 'period']

    def __init__(self, *args, **kwargs):
        super(PurchaseOrderItemsModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class':'form-control w3-input w3-border w3-round-large w3-margin-bottom',
                'placeholder': field.label
            })
        if 'DELETE' in self.fields:
            self.fields['DELETE'].label = 'ລຶບ'
    
# Inline Formset for PO Items Model 
PoItemsFormSet = inlineformset_factory(
    PurchaseOrderModel,
    PurchaseOrderItemsModel,
    form = PurchaseOrderItemsModelForm,
    extra=1,
    can_delete=True,
)