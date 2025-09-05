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
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, UpdateView, CreateView, FormView, TemplateView, DeleteView, View
#=====[ Third-party Packages ]=====
from django_ratelimit.decorators import ratelimit
from weasyprint import HTML
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied, ValidationError

# Loging
import logging

### Modle and Form
from .models import ContractsModel
from .forms import ContractsModelForm
from apps.app_customers.models import CustomersModel
from apps.app_employee.models import EmployeesModel
from apps.app_quotations.models import QuotationInformationModel
from apps.app_invoices.models import InvoiceModel
from apps.app_po.models import PurchaseOrderModel


logger = logging.getLogger(__name__)

# Home View 
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class ContractsListView(LoginRequiredMixin, ListView):
    login_url = 'users:login'
    model = ContractsModel
    template_name = 'app_contracts/home.html'
    context_object_name = 'all_contracts'

    def get_queryset(self):
        queryset = super().get_queryset()
        # search function 
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(contract_id__icontains = search ) |
                Q(customer__company_name__icontains = search) |
                Q(customer__contact_person_name__icontains = search) |
                Q(po__po_id__icontains = search)
            )

        # Order by status 
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status = status)

        # order by contract
        start_contract = self.request.GET.get('start_contract', '')
        end_contract = self.request.GET.get('end_contract', '')

        if start_contract:
            queryset = queryset.filter(start_contract__range = [start_contract, end_contract])
        elif start_contract:
            queryset = queryset.filter(start_contract__gte = start_contract)
        elif end_contract:
            queryset = queryset.filter(start_contract__lte = end_contract)
        
        # Default order by
        queryset = queryset.order_by('-end_contract')
        return queryset
    
    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        context['title'] = 'ລາຍການສັນຍາທັ່ງຫມົດ'
        context['search'] = self.request.GET.get('search', '')
        context['status_list'] = ContractsModel.ContractStatus.choices
        return context
        


# Create View From App PO
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class ContractsCreateView(LoginRequiredMixin, View):
    """
    Create a new contract from an existing PO.
    Prepopulates contract form with data from PO.
    Redirects to existing contract if one already exists.
    """
    liogin_url = 'users:login'
    template_name = 'app_contracts/create_contract.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to preload PO and check for existing contract.
        This avoids repeating code in get() and post().
        """
        self.po_id = self.kwargs.get('po_id')
        self.po = get_object_or_404(PurchaseOrderModel, po_id = self.po_id)
        self.existing_contract = ContractsModel.objects.filter(po=self.po).first()
        return super().dispatch(request, *args, **kwargs)
    
    def _check_existing_contract_redirect(self, request, redirect_view='app_contracts:update_contract'):
        """
        Helper method to handle redirect if a contract already exists.
        Returns a redirect response or None if no existing contract.
        """
        if self.existing_contract:
            if redirect_view == 'app_contracts:update_contract':
                messages.warning(request, 'ມີສັນຍາສະບັບນີ້ໃນລະບົບແລ້ວ, ກຳລັງເປີດຫນ້າແກ້ໄຂສັນຍາ')
            else:
                messages.warning(request, 'ມີສັນຍາສະບັບນີ້ໃນລະບົບແລ້ວ, ບໍ່ສ້າມາດສ້າງໃຫມ່ໄດ້')
            return redirect(redirect_view, contract_id = self.existing_contract.contract_id)
        return None
    
    def _get_initial_data_from_po(self):
        """
        Extract relevant fields from PO to prepopulate contract form.
        """
        # Get customer from PO - adjust this based on your PO model structure
        customer = getattr(self.po, 'customer', None)
        if not customer:
            # Try to get customer from related models if noe directly on PO
            customer = getattr(self.po, 'quotation__customer', None)
        
        # Get employee from request user
        employee = self.request.user.employee if hasattr(self.request.user, 'employee') else None

        quotation = getattr(self.po, 'quotation', None)
        invoice = getattr(self.po, 'invoice', None)

        return {
            'customer':customer,
            'created_by':employee,
            'quotation':quotation,
            'invoice':invoice,
            'po':self.po,
        }
    
    def get(self, request, *args, **kwargs):
        # Check for existing contract
        redirect_response = self._check_existing_contract_redirect(request)
        if redirect_response:
            return redirect_response
        
        # Initailize contract form with data from PO
        initial_data = self._get_initial_data_from_po()
        form = ContractsModelForm(initial = initial_data)

        # set readonly or disable fields for relate documents
        form.fields['quotation'].disabled = True
        form.fields['invoice'].disabled = True
        form.fields['po'].disabled = True
        form.fields['customer'].disabled = True

        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        redirect_response = self._check_existing_contract_redirect(
            request,
            redirect_view = 'app_contracts:create_contract',
        )
        if redirect_response:
            return redirect_response
        
        form = ContractsModelForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    contract = form.save(commit=False)

                    # Ling contract to PO
                    contract.po = self.po
                    # if not set in form, set the related document from PO
                    if not contract.quotation and hasattr(self.po, 'quotation'):
                        contract.quotation = self.po.quotation
                    if not contract.invoice and hasattr(self.po, 'invoice'):
                        contract.invoice = self.po.invoice
                    if not contract.customer and hasattr(self.po, 'customer'):
                        contract.customer = self.po.customer

                    # Assign created_by employee from request user
                    if hasattr(request.user, 'employee'):
                        contract.created_by = self.request.user.employee

                    # Validate the contract dates
                    contract.clean()

                    # Save the Contract
                    contract.save()
                    # Return message
                    messages.success(request, "ອອກສັນຍາໃຫມ່ສະເລັດ")
                    # return redirect('app_contracts:contract_details', contract_id = contract.contract_id)
                    return redirect('app_contracts:home')
            except ValidationError as e:
                messages.error(request, f"ປ້ອນຂ້ມູນຜິດພາດ: {e}")
            except Exception as e:
                messages.error(request, f"ເກີດຂໍ້ຜິດພາດໃນການສ້າງສັນຍາ {str(e)}")

        else:
            messages.error(request, "ກະລຸນາແກ້ໄຂຂໍ້ມູນທີ່ຜິດພາດຂ້າງລຸ່ມນີ້")
            print(form.errors)
        
        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)
    
    
    def _get_context_data(self, **kwargs):
        """
        Assemble context for template rendering.
        """
        context = kwargs.copy()
        context.update({
            'title':'ສ້າງສັນຍາໃຫມ່',
            'po':self.po,
            'existing_contract':self.existing_contract,
        })
        return context
    
# View Contract Details
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class ContractDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    template_name = 'app_contracts/contract_details.html'
    model = ContractsModel
    context_object_name = 'all_contracts'
    slug_field = 'contract_id'
    slug_url_kwarg = 'contract_id'


# Update Contract View
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class UpdateContractView(LoginRequiredMixin, View):
    """
    Update and exising contract.
    Preload contract by contract_id
    """
    login_url = 'users:login'
    template_name = 'app_contracts/create_contract.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Load contract by contract_id from URL
        """
        self.contract_id = self.kwargs.get('contract_id')
        self.contract = get_object_or_404(ContractsModel, contract_id = self.contract_id)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Render update form with existing contract data
        """
        form = ContractsModelForm(instance = self.contract)

        # Disable related ducument fields
        form.fields['quotation'].disabled = True
        form.fields['invoice'].disabled = True
        form.fields['po'].disabled = True
        form.fields['customer'].disabled = True

        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """
        Handle update contract form submission
        """
        form = ContractsModelForm(request.POST, request.FILES, instance = self.contract)
        if form.is_valid():
            try:
                with transaction.atomic():
                    contract = form.save(commit=False)
                    
                    # Validate the contract date
                    contract.clean()

                    # save the contract
                    contract.save()
                    # Return message
                    messages.success(request, 'ແກ້ໄຂສັນຍາສຳເລັດ')
                    return redirect('app_contracts:contract_details', contract_id = contract.contract_id)
            except ValidationError as e:
                messages.error(request, f"ປ້ອນຂໍ້ມູນຜິດພາດ {e}")
                print(f"update contract form errors: {form.errors}")

            except Exception as e:
                messages.error(request, f"ເກີດຂໍ້ຜິດພາດໃນການແກ້ໄຂສັນຍາ {str(e)}")
                print(f"update contract form errors: {form.errors}")
        else:
            messages.error(request, "ກະລຸນາແກ້ໄຂຂໍ້ມູນທີ່ຜິດພາດຂ້າງລຸ່ມນີ້")
            print(form.errors)
        
        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)

    
    def _get_context_data(self, **kwargs):
        """
        Assemble context for template rendering
        """
        context = kwargs.copy()
        context.update({
            'title':f'ແກ້ໄຂສັນຍາ {self.kwargs.get('contract_id')}',
            'contract':self.contract,
        })
        return context
    
# Delete contract view
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class ContractDeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'users:login'
    model = ContractsModel
    template_name = 'app_contracts/components/delete.html'
    success_url = reverse_lazy('app_contracts:home')
    slug_field = 'contract_id'
    slug_url_kwarg = 'contract_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"ລຶບສັນຍາ {self.kwargs.get('contract_id')}"

        return context