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
from django.core.exceptions import PermissionDenied

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
class ContractsListView(LoginRequiredMixin, ListView):
    login_url = 'users:login'
    model = ContractsModel
    template_name = 'app_contracts/home.html'
    context_object_name = 'all_contracts'


# Create View From App PO
class ContractsCreateView(LoginRequiredMixin, View):
    """
    Create a new contract from an existing PO.
    Prepopulates contract form with data from PO.
    Redirects to existing contract if one already exists.
    """
    login_url = 'users:login'
    template_name = 'app_contracts/create_contract.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to preload PO and check for existing contract.
        This avoids repeating code in get() and post().
        """
        self.po_id = self.kwargs.get('po_id')
        self.po = get_object_or_404(PurchaseOrderModel, po_id=self.po_id)
        self.existing_contract = ContractsModel.objects.filter(po=self.po).first()
        return super().dispatch(request, *args, **kwargs)

    def _check_existing_contract_redirect(self, request, redirect_view='app_contracts:update_contract'):
        """
        Helper method to handle redirect if a contract already exists.
        Returns a redirect response or None if no existing contract.
        """
        if self.existing_contract:
            if redirect_view == 'app_contracts:update_contract':
                messages.warning(request, "This contract already exists. Opening for editing.")
            else:
                messages.warning(request, "This contract already exists. Cannot create a new one.")
            return redirect(redirect_view, contract_id=self.existing_contract.contract_id)
        return None

    def _get_initial_data_from_po(self):
        """
        Extract relevant fields from PO to prepopulate contract form.
        Adjust field names according to your ContractsModelForm.
        """
        return {
            'customer': getattr(self.po, 'customer', None),
            'employee': getattr(self.po, 'created_by', None),
            'start_contract': getattr(self.po, 'start_date', None),
            'end_contract': getattr(self.po, 'end_date', None),
            'status': ContractsModel.ContractStatus.DRAFT,
            # Add other fields to copy from PO as needed
        }

    def get(self, request, *args, **kwargs):
        # Check for existing contract
        redirect_response = self._check_existing_contract_redirect(request)
        if redirect_response:
            return redirect_response

        # Initialize form with data from PO
        form = ContractsModelForm(initial=self._get_initial_data_from_po())

        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Check for existing contract
        redirect_response = self._check_existing_contract_redirect(
            request,
            redirect_view='app_contracts:contract_details'
        )
        if redirect_response:
            return redirect_response

        form = ContractsModelForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    contract = form.save(commit=False)
                    # Link contract to PO
                    contract.po = self.po
                    # Assign created_by employee from request.user
                    contract.created_by = getattr(request.user, 'employee', None)
                    contract.save()
                    messages.success(request, "Contract created successfully.")
                    return redirect('app_contracts:contract_details', contract_id=contract.contract_id)
            except Exception as e:
                # Log exception if you have logger configured
                # logger.exception(e)
                messages.error(request, f"An error occurred while creating the contract: {str(e)}")

        context = self._get_context_data(form=form)
        return render(request, self.template_name, context)

    def _get_context_data(self, **kwargs):
        """
        Assemble context for template rendering.
        """
        context = kwargs.copy()  # Use kwargs to pass form or other variables
        context.update({
            'title': 'Create New Contract',
            'po': self.po,
            'existing_contract': self.existing_contract,
        })
        return context