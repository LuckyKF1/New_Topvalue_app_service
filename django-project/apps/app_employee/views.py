# coding=utf-8

#=====[ Built-in / Standard Library ]=====
import re
import tempfile

#=====[ Django Core Imports ]=====
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, UpdateView
from django_ratelimit.decorators import ratelimit
#Login Request and rate_limit
#Import forms and models
from .forms import EmployeesModelForm
from .models import EmployeesModel


@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class HomeView(LoginRequiredMixin, ListView):
    """
    CBV for listing all employee.
    """
    login_url = 'users:login'
    model = EmployeesModel
    template_name = 'app_employee/home.html'
    context_object_name = 'all_employee'

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                employee_name__icontains = search
            ) | queryset.filter(
                employee_lastname__icontains = search
            ) | queryset.filter(
                department__icontains = search
            )
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['title'] = 'ພະນັກງານທັ່ງຫມົດ'
        return context
    

@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class Details(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = EmployeesModel
    context_object_name = 'one_employee'
    template_name = 'app_employee/details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']='ລາຍລະອຽດຂອງພະນັກງານ'
        return context
    

@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class EditEmpView(LoginRequiredMixin, UpdateView):
    login_url = 'users:login'
    model = EmployeesModel
    form_class = EmployeesModelForm
    template_name = 'app_employee/edit.html'
    context_object_name = 'edit_emp'

    def get_success_url(self):
        return reverse('app_employee:details', kwargs={'pk':self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']='ແກ້ໄຂຂໍ້ມູນພະນັກງານ'
        return context

#====================================== Home page and list of add employee ======================================
@login_required
@ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True)
def add(request):
    """
    Add a new employie.
    """
    if request.method == 'POST':
        form = EmployeesModelForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'ສ້າງບັນຊີພະນັກງານໃຫມ່ສຳເລັດ')
            return redirect('app_employee:home')
        else:
            messages.error(request, 'ສ້າງບັນຊີພະນັກງານລົ້ມເຫລວ')
            print(f" add_employee form errors: {form.errors}")
    else:
        form = EmployeesModelForm()
    context = {
        'title': 'ສ້າງບັນຊີພະນັກງານ',
        'form': form
    }
    return render(request, 'app_employee/add.html', context)