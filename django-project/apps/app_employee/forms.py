# coding=utf-8
from django import forms
from django.forms import ModelForm
from .models import EmployeesModel


class EmployeesModelForm(forms.ModelForm):
    class Meta:
        model = EmployeesModel
        fields = ['user', 'employee_name', 'employee_lastname', 'department', 'signature']
        labels = {
            'employee_name':'ຊື່ພະນັກງານ',
            'employee_lastname':'ນາມສະກຸນ',
            'department':'ພະແນກ',
            'signature':'ອັບໂຫລດກາຈ້ຳແລະລາຍເຊັນຂອງພະນັກງານ',
        }
        widgets = {
            'signature':forms.ClearableFileInput(attrs={'class':'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css_class = 'form-control w3-input w3-border w3-round w3-margin-bottom'

        for field_name, field_object in self.fields.items():
            if not isinstance(field_object.widget, forms.ClearableFileInput):
                current_classes = field_object.widget.attrs.get('class', '')
                field_object.widget.attrs['class'] = f"{current_classes} {css_class}".strip()