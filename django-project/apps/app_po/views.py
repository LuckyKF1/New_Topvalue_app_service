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
from .models import PurchaseOrderModel, PurchaseOrderItemsModel
from .forms import PurchaseOrderModelForm, PoItemsFormSet
from apps.app_quotations.models import QuotationInformationModel
from apps.app_employee.models import EmployeesModel
from apps.app_invoices.models import InvoiceModel
import logging

logger = logging.getLogger(__name__)


# Class Base Views
# Home
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class HomeView(LoginRequiredMixin, ListView):
    login_url = 'users:login'
    model = PurchaseOrderModel
    template_name = 'app_po/home.html'
    context_object_name = 'all_po'

    def get_queryset(self):
        queryset = super().get_queryset()

        # Search / Filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(po_id__icontains=search) |
                Q(customer__company_name__icontains=search) |
                Q(customer__contact_person_name__icontains=search)
            )
        
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Date filter
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if start_date and end_date:
            queryset = queryset.filter(start_date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(start_date__lte=end_date)

        # Default order
        return queryset.order_by('-end_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ລາຍການໃບສັ່ງຊື້ສິນຄ້າ'
        context['search'] = self.request.GET.get('search', '')
        context['status_list'] = PurchaseOrderModel.PoStatus.choices
        return context



# Create View 
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class PurchaseOrderCreateView(LoginRequiredMixin, View):
    """
    View for creating Purchase Orders from existing invoices.
    Handles duplicate PO prevention and formset creation.
    """
    login_url = 'users:login'
    template_name = 'app_po/create_po.html'

    def dispatch(self, request, *args, **kwargs):
        """Common setup for both GET and POST requests."""
        self.invoice_id = self.kwargs.get('invoice_id')
        self.invoice = get_object_or_404(InvoiceModel, invoice_id=self.invoice_id)
        self.quotation = self.invoice.quotation
        
        # Check for existing PO early
        self.existing_po = PurchaseOrderModel.objects.filter(
            invoice=self.invoice
        ).first()
        
        return super().dispatch(request, *args, **kwargs)

    def _get_initial_items(self):
        """Extract initial items data from quotation."""
        return [
            {
                'product_name': item.product_name,
                'price': item.price,
                'qty': item.qty,
                'period': item.period,
            }
            for item in self.quotation.items.all()
        ]

    def _create_items_formset(self, data=None, instance=None):
        """Create and configure the items formset."""
        initial_items = self._get_initial_items()
        
        PoItemsFormSetNew = inlineformset_factory(
            PurchaseOrderModel,
            PurchaseOrderItemsModel,
            form=PoItemsFormSet.form,
            extra=len(initial_items),
            can_delete=False
        )
        
        # Use proper instance or create temporary one
        formset_instance = instance or PurchaseOrderModel()
        queryset = (
            PurchaseOrderItemsModel.objects.none() 
            if not instance or not instance.pk 
            else instance.items.all()
        )
        
        return PoItemsFormSetNew(
            data=data,
            instance=formset_instance,
            queryset=queryset,
            initial=initial_items if not instance or not instance.pk else None
        )

    def _get_context_data(self, form, items_formset):
        """Build context data for template rendering."""
        return {
            'form': form,
            'items': items_formset,
            'title': 'ສ້າງໃບສັ່ງຊື້',
            'invoice': self.invoice,
            'quotation': self.quotation,
        }

    def get(self, request, *args, **kwargs):
        """Handle GET request - display the PO creation form."""
        # Redirect if PO already exists
        if self.existing_po:
            messages.warning(
                request,
                "ໃບສັ່ງຊື້ນີ້ໄດ້ຖືກສ້າງແລ້ວ, ກຳລັງເປີດຫນ້າແກ້ໄຂໃບສັ່ງຊື້"
            )
            return redirect('app_po:update_po', po_id=self.existing_po.po_id)

        # Create new PO form
        form = PurchaseOrderModelForm(initial={
            'quotation': self.quotation,
            'invoice': self.invoice,
        })
        
        items_formset = self._create_items_formset()
        context = self._get_context_data(form, items_formset)
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle POST request - process PO creation."""
        # Prevent duplicate PO creation
        if self.existing_po:
            messages.warning(request, "ໃບສັ່ງຊື້ນີ້ໄດ້ຖືກສ້າງແລ້ວ")
            return redirect('app_po:po_details', po_id=self.existing_po.po_id)

        form = PurchaseOrderModelForm(request.POST, request.FILES)
        
        if form.is_valid():
            return self._handle_valid_form(request, form)
        else:
            # Form is invalid - redisplay with errors
            items_formset = self._create_items_formset(data=request.POST)
            context = self._get_context_data(form, items_formset)
            return render(request, self.template_name, context)

    def _handle_valid_form(self, request, form):
        """Process valid form submission with transaction safety."""
        try:
            with transaction.atomic():
                # Create PO instance
                po = form.save(commit=False)
                po.created_by = self._get_employee(request.user)
                po.invoice = self.invoice
                po.save()

                # Process items formset
                items_formset = self._create_items_formset(
                    data=request.POST, 
                    instance=po
                )
                
                if items_formset.is_valid():
                    items_formset.save()
                    messages.success(
                        request, 
                        "ໃບສັ່ງຊື້ໄດ້ຖືກສ້າງສຳເລັດແລ້ວ"
                    )
                    return redirect('app_po:po_details', po_id=po.po_id)
                else:
                    # Log formset errors for debugging
                    logger.error(
                        f"PO items formset validation failed for invoice {self.invoice_id}: "
                        f"{items_formset.errors}"
                    )
                    # Transaction will rollback automatically
                    raise ValueError("Items formset validation failed")
                    
        except Exception as e:
            logger.error(
                f"Error creating PO for invoice {self.invoice_id}: {str(e)}"
            )
            messages.error(
                request, 
                "ເກີດຂໍ້ຜິດພາດໃນການສ້າງໃບສັ່ງຊື້, ກະລຸນາລອງໃໝ່"
            )
            
        # If we reach here, there was an error
        items_formset = self._create_items_formset(data=request.POST)
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def _get_employee(self, user):
        """Get employee instance for the current user."""
        try:
            return EmployeesModel.objects.get(user=user)
        except EmployeesModel.DoesNotExist:
            logger.error(f"Employee not found for user {user.id}")
            raise ValueError(f"Employee profile not found for user {user.username}")

    def get_context_data(self, **kwargs):
        """
        Additional context data method for potential future use.
        Can be overridden in subclasses if needed.
        """
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}
        context.update({
            'invoice': self.invoice,
            'quotation': self.quotation,
        })
        return context

# Delete View
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class DeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'users:login'
    model = PurchaseOrderModel
    template_name = 'app_po/components/delete.html'
    success_url = reverse_lazy('app_po:home')
    slug_field = 'po_id'
    slug_url_kwarg = 'po_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"ລຶບໃບສັ່ງຊື້ນີ້ {self.kwargs.get('po_id')}"
        return context
    
    def get_success_url(self):
        messages.success(self.request, 'ລຶບໃບສັ່ງຊື້ສຳເັລດ')
        return reverse_lazy('app_po:home')
    


# Details View
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class InvoiceDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = PurchaseOrderModel
    template_name  = 'app_po/components/po_details.html'
    context_object_name = 'purchase_order'
    slug_field = 'po_id'
    slug_url_kwarg = 'po_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'ລາຍລະອຽດໃບສັ່ງຊື້ {self.kwargs.get('po_id')}'
        return context


# Update View 
class PurchaseOrderUpdateView(LoginRequiredMixin, View):
    """
    View for updating existing Purchase Orders.
    Handles form validation, item management, and permission checks.
    """
    login_url = 'users:login'
    template_name = 'app_po/create_po.html'

    def dispatch(self, request, *args, **kwargs):
        """Common setup for both GET and POST requests."""
        self.po_id = self.kwargs.get('po_id')
        self.po = get_object_or_404(PurchaseOrderModel, po_id=self.po_id)
        self.invoice = self.po.invoice
        self.quotation = self.invoice.quotation
        
        # Check permissions
        if not self._has_update_permission(request.user):
            raise PermissionDenied("You don't have permission to update this Purchase Order")
        
        return super().dispatch(request, *args, **kwargs)

    def _has_update_permission(self, user):
        """
        Check if user has permission to update this PO.
        Override this method to implement custom permission logic.
        """
        try:
            employee = EmployeesModel.objects.get(user=user)
            # Basic permission check - can be expanded based on business rules
            return (
                self.po.created_by == employee or
                user.is_superuser or
                user.has_perm('app_po.change_purchaseordermodel')
            )
        except EmployeesModel.DoesNotExist:
            logger.warning(f"Employee not found for user {user.id} attempting to update PO {self.po_id}")
            return False

    def _can_edit_po(self):
        """
        Check if PO is in a state that allows editing.
        Override this method to implement status-based editing rules.
        """
        # Add your business logic here
        # For example: return self.po.status in ['draft', 'pending']
        return True  # Default: allow editing

    def _create_items_formset(self, data=None):
        """Create and configure the items formset for updates."""
        PoItemsFormSetUpdate = inlineformset_factory(
            PurchaseOrderModel,
            PurchaseOrderItemsModel,
            form=PoItemsFormSet.form,
            extra=1,  # Allow adding one new item
            can_delete=True,  # Allow deletion in update mode
            min_num=1,  # Require at least one item
            validate_min=True
        )
        
        return PoItemsFormSetUpdate(
            data=data,
            instance=self.po,
            queryset=self.po.items.all()
        )

    def _get_context_data(self, form, items_formset, **extra_context):
        """Build context data for template rendering."""
        context = {
            'form': form,
            'items': items_formset,
            'title': 'ແກ້ໄຂໃບສັ່ງຊື້',
            'po': self.po,
            'invoice': self.invoice,
            'quotation': self.quotation,
            'can_edit': self._can_edit_po(),
            'is_update': True,
        }
        context.update(extra_context)
        return context

    def get(self, request, *args, **kwargs):
        """Handle GET request - display the PO update form."""
        # Check if PO can be edited
        if not self._can_edit_po():
            messages.warning(
                request,
                "ໃບສັ່ງຊື້ນີ້ບໍ່ສາມາດແກ້ໄຂໄດ້ເນື່ອງຈາກສະຖານະປັດຈຸບັນ"
            )
            return redirect('app_po:po_details', po_id=self.po.po_id)

        # Initialize form with existing PO data
        form = PurchaseOrderModelForm(instance=self.po)
        items_formset = self._create_items_formset()
        
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle POST request - process PO updates."""
        # Check if PO can be edited
        if not self._can_edit_po():
            messages.error(
                request,
                "ໃບສັ່ງຊື້ນີ້ບໍ່ສາມາດແກ້ໄຂໄດ້ເນື່ອງຈາກສະຖານະປັດຈຸບັນ"
            )
            return redirect('app_po:po_details', po_id=self.po.po_id)

        form = PurchaseOrderModelForm(
            request.POST, 
            request.FILES, 
            instance=self.po
        )
        
        if form.is_valid():
            return self._handle_valid_form(request, form)
        else:
            # Form is invalid - redisplay with errors
            items_formset = self._create_items_formset(data=request.POST)
            context = self._get_context_data(form, items_formset)
            return render(request, self.template_name, context)

    def _handle_valid_form(self, request, form):
        """Process valid form submission with transaction safety."""
        try:
            with transaction.atomic():
                # Update PO instance
                po = form.save(commit=False)
                po.updated_by = self._get_employee(request.user)
                po.save()

                # Process items formset
                items_formset = self._create_items_formset(data=request.POST)
                
                if items_formset.is_valid():
                    items_formset.save()
                    
                    # Log successful update
                    logger.info(
                        f"PO {po.po_id} updated successfully by user {request.user.id}"
                    )
                    
                    messages.success(
                        request, 
                        "ໃບສັ່ງຊື້ໄດ້ຖືກອັບເດດສຳເລັດແລ້ວ"
                    )
                    return redirect('app_po:po_details', po_id=po.po_id)
                else:
                    # Log formset errors for debugging
                    logger.error(
                        f"PO items formset validation failed for PO {self.po_id}: "
                        f"{items_formset.errors}"
                    )
                    # Transaction will rollback automatically
                    raise ValueError("Items formset validation failed")
                    
        except Exception as e:
            logger.error(
                f"Error updating PO {self.po_id}: {str(e)}"
            )
            messages.error(
                request, 
                "ເກີດຂໍ້ຜິດພາດໃນການອັບເດດໃບສັ່ງຊື້, ກະລຸນາລອງໃໝ່"
            )
            
        # If we reach here, there was an error
        items_formset = self._create_items_formset(data=request.POST)
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def _get_employee(self, user):
        """Get employee instance for the current user."""
        try:
            return EmployeesModel.objects.get(user=user)
        except EmployeesModel.DoesNotExist:
            logger.error(f"Employee not found for user {user.id}")
            raise ValueError(f"Employee profile not found for user {user.username}")

    def get_context_data(self, **kwargs):
        """
        Additional context data method for potential future use.
        Can be overridden in subclasses if needed.
        """
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}
        context.update({
            'po': self.po,
            'invoice': self.invoice,
            'quotation': self.quotation,
            'is_update': True,
        })
        return context
