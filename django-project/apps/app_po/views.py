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
from apps.app_customers.models import CustomerTenantModel
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
        start_date = self.request.GET.get('start_date', '')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        # Default order
        return queryset.order_by('-start_date')
    
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
    Create a Purchase Order (PO) from an existing Invoice.
    Auto-creates Tenant if tenant_name/tenant_domain are provided.
    Prepopulates PO items from quotation items.
    """

    login_url = 'users:login'  # Redirect to login page if user is not authenticated
    template_name = 'app_po/create_po.html'  # Template used for rendering the PO form

    def dispatch(self, request, *args, **kwargs):
        # Extract invoice_id from URL kwargs
        self.invoice_id = self.kwargs.get('invoice_id')
        # Fetch the invoice or return 404 if it does not exist
        self.invoice = get_object_or_404(InvoiceModel, invoice_id=self.invoice_id)
        # Get the related quotation from the invoice
        self.quotation = self.invoice.quotation
        # Get the customer linked to the quotation
        self.customer = self.quotation.customer
        # Check if a Purchase Order already exists for this invoice
        self.existing_po = PurchaseOrderModel.objects.filter(invoice=self.invoice).first()
        return super().dispatch(request, *args, **kwargs)

    def _get_initial_items(self):
        # Prepare initial data for PO items formset based on quotation items
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
        # Create an inline formset for PO items, prefilled from quotation
        initial_items = self._get_initial_items()
        PoItemsFormSetNew = inlineformset_factory(
            parent_model=PurchaseOrderModel,
            model=PurchaseOrderItemsModel,
            form=PoItemsFormSet.form,  # Custom form for PO items
            extra=len(initial_items),   # Number of extra blank forms = number of quotation items
            can_delete=False            # Prevent deletion of items in formset
        )

        # Decide which instance the formset is bound to (existing PO or new)
        formset_instance = instance or PurchaseOrderModel()

        # Set queryset: empty if creating new, otherwise use existing PO items
        queryset = (
            PurchaseOrderItemsModel.objects.none()
            if not instance or not instance.pk
            else instance.items.all()
        )

        # Return the formset instance with initial items if creating new PO
        return PoItemsFormSetNew(
            data=data,
            instance=formset_instance,
            queryset=queryset,
            initial=initial_items if not instance or not instance.pk else None
        )

    def _get_context_data(self, form, items_formset):
        # Build context for rendering template
        return {
            'form': form,                # Main PO form
            'items': items_formset,      # Inline items formset
            'title': 'ສ້າງໃບສັ່ງຊື້',   # Page title
            'invoice': self.invoice,      # Pass invoice to template
            'quotation': self.quotation,  # Pass quotation to template
            'customer': self.customer,    # Pass customer to template
        }

    def get(self, request, *args, **kwargs):
        # Handle GET request (display form)
        if self.existing_po:
            # If PO already exists, redirect to update page with warning
            messages.warning(request, "ໃບສັ່ງຊື້ນີ້ໄດ້ຖືກສ້າງແລ້ວ, ກຳລັງເປີດຫນ້າແກ້ໄຂ")
            return redirect('app_po:update_po', po_id=self.existing_po.po_id)

        # Create a new PO form pre-filled with invoice, quotation, customer
        form = PurchaseOrderModelForm(initial={
            'quotation': self.quotation,
            'invoice': self.invoice,
            'customer': self.customer,
        })

        # Create items formset
        items_formset = self._create_items_formset()

        # Build context and render template
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Handle POST request (form submission)
        if self.existing_po:
            # If PO already exists, prevent duplicate creation
            messages.warning(request, "ໃບສັ່ງຊື້ນີ້ໄດ້ຖືກສ້າງແລ້ວ")
            return redirect('app_po:po_details', po_id=self.existing_po.po_id)

        # Bind form to POST data
        form = PurchaseOrderModelForm(request.POST, request.FILES)
        if form.is_valid():
            # If main form is valid, handle saving inside transaction
            return self._handle_valid_form(request, form)

        # If form is invalid, recreate items formset with POST data
        items_formset = self._create_items_formset(data=request.POST)
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def _handle_valid_form(self, request, form):
        try:
            with transaction.atomic():  # Ensure all DB operations succeed or rollback
                # Auto-create tenant if tenant_name and tenant_domain are provided
                tenant_name = form.cleaned_data.pop('tenant_name', None)
                tenant_domain = form.cleaned_data.pop('tenant_domain', None)
                tenant = None
                if tenant_name and tenant_domain:
                    tenant = CustomerTenantModel.objects.create(
                        tenant_name=tenant_name,
                        tenant_domain=tenant_domain
                    )
                    # Link tenant to customer
                    self.customer.tenant = tenant
                    self.customer.save()

                # Save PO instance without committing to DB yet
                po = form.save(commit=False)
                po.created_by = self._get_employee(request.user)  # Assign employee
                po.invoice = self.invoice
                po.customer = self.customer
                po.tenant = tenant
                po.save()  # Save PO to DB

                # Save items formset
                items_formset = self._create_items_formset(data=request.POST, instance=po)
                if items_formset.is_valid():
                    items_formset.save()  # Save all items
                    messages.success(request, "ໃບສັ່ງຊື້ໄດ້ຖືກສ້າງສຳເລັດແລ້ວ")
                    return redirect('app_po:po_details', po_id=po.po_id)
                else:
                    # Raise exception if items are invalid
                    raise ValueError("Items formset validation failed")

        except Exception as e:
            # Log any errors and display message to user
            logger.exception(f"Error creating PO for invoice {self.invoice_id}: {str(e)}")
            messages.error(request, "ເກີດຂໍ້ຜິດພາດໃນການສ້າງໃບສັ່ງຊື້")

        # Re-render form with items formset after error
        items_formset = self._create_items_formset(data=request.POST)
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def _get_employee(self, user):
        # Retrieve the employee instance linked to the logged-in user
        try:
            return EmployeesModel.objects.get(user=user)
        except EmployeesModel.DoesNotExist:
            # Log and raise exception if no employee found
            logger.error(f"Employee not found for user {user.id}")
            raise ValueError(f"Employee profile not found for user {user.username}")

    def get_context_data(self, **kwargs):
        """
        Note: This method is not used by View directly (TemplateView uses it).
        You already assemble context via _get_context_data() in get()/post().

        Keep it only if you plan to subclass from a mixin that calls get_context_data().
        Otherwise it can be removed to avoid confusion.
        """
        context = (
            super().get_context_data(**kwargs)
            if hasattr(super(), 'get_context_data')
            else {}
        )
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
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class PurchaseOrderUpdateView(LoginRequiredMixin, View):
    """
    View for updating existing Purchase Orders.
    Handles form validation, item management, and tenant assignment.
    """
    login_url = 'users:login'
    template_name = 'app_po/create_po.html'

    def dispatch(self, request, *args, **kwargs):
        self.po_id = self.kwargs.get('po_id')
        self.po = get_object_or_404(PurchaseOrderModel, po_id=self.po_id)
        self.invoice = self.po.invoice
        self.quotation = self.invoice.quotation
        self.customer = self.quotation.customer   # keep reference to customer

        if not self._has_update_permission(request.user):
            raise PermissionDenied("You don't have permission to update this Purchase Order")
        
        return super().dispatch(request, *args, **kwargs)

    def _has_update_permission(self, user):
        try:
            employee = EmployeesModel.objects.get(user=user)
            return (
                self.po.created_by == employee or
                user.is_superuser or
                user.has_perm('app_po.change_purchaseordermodel')
            )
        except EmployeesModel.DoesNotExist:
            logger.warning(f"Employee not found for user {user.id} attempting to update PO {self.po_id}")
            return False

    def _can_edit_po(self):
        return True

    def _create_items_formset(self, data=None):
        PoItemsFormSetUpdate = inlineformset_factory(
            PurchaseOrderModel,
            PurchaseOrderItemsModel,
            form=PoItemsFormSet.form,
            extra=1,
            can_delete=True,
            min_num=1,
            validate_min=True
        )
        return PoItemsFormSetUpdate(
            data=data,
            instance=self.po,
            queryset=self.po.items.all()
        )

    def _get_context_data(self, form, items_formset, **extra_context):
        context = {
            'form': form,
            'items': items_formset,
            'title': 'ແກ້ໄຂໃບສັ່ງຊື້',
            'po': self.po,
            'invoice': self.invoice,
            'quotation': self.quotation,
            'customer': self.customer,
            'can_edit': self._can_edit_po(),
            'is_update': True,
        }
        context.update(extra_context)
        return context

    def get(self, request, *args, **kwargs):
        if not self._can_edit_po():
            messages.warning(request, "ໃບສັ່ງຊື້ນີ້ບໍ່ສາມາດແກ້ໄຂໄດ້ເນື່ອງຈາກສະຖານະ")
            return redirect('app_po:po_details', po_id=self.po.po_id)

        initial_data = {
            'customer': self.customer
        }

        #prefill tanent data
        if self.customer.tenant:
            initial_data.update({
                'tenant_name' : self.customer.tenant.tenant_name,
                'tenant_domain': self.customer.tenant.tenant_domain,
            })
        form = PurchaseOrderModelForm(
            instance=self.po,
            initial= initial_data
        )
        items_formset = self._create_items_formset()
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if not self._can_edit_po():
            messages.error(request, "ໃບສັ່ງຊື້ນີ້ບໍ່ສາມາດແກ້ໄຂໄດ້ເນື່ອງຈາກສະຖານະ")
            return redirect('app_po:po_details', po_id=self.po.po_id)

        form = PurchaseOrderModelForm(request.POST, request.FILES, instance=self.po)
        if form.is_valid():
            return self._handle_valid_form(request, form)
        else:
            items_formset = self._create_items_formset(data=request.POST)
            context = self._get_context_data(form, items_formset)
            return render(request, self.template_name, context)

    def _handle_valid_form(self, request, form):
        try:
            with transaction.atomic():
                # craete or update tenant if tenant_name/tenant_domain are provided
                tenant_name = form.cleaned_data.pop('tenant_name', None)
                tenant_domain = form.cleaned_data.pop('tenant_domain', None)
                tenant = self.customer.tenant  # default usd current tenant
                if tenant_name and tenant_domain:
                    if tenant:
                        # update tenant
                        tenant.tenant_name = tenant_name
                        tenant.tenant_domain = tenant_domain
                        tenant.save()
                    else:
                        # create tenant
                        tenant = CustomerTenantModel.objects.create(
                            tenant_name=tenant_name,
                            tenant_domain=tenant_domain
                        )
                    # connect tenant backto customer
                    self.customer.tenant = tenant
                    self.customer.save()

                po = form.save(commit=False)
                po.updated_by = self._get_employee(request.user)
                po.customer = self.customer
                po.tenant = tenant
                po.save()

                items_formset = self._create_items_formset(data=request.POST)
                if items_formset.is_valid():
                    items_formset.save()
                    messages.success(request, "ໃບສັ່ງຊື້ໄດ້ຖືກອັບເດດສຳເລັດແລ້ວ")
                    return redirect('app_po:po_details', po_id=po.po_id)
                else:
                    raise ValueError("Items formset validation failed")
        except Exception as e:
            logger.error(f"Error updating PO {self.po_id}: {str(e)}")
            messages.error(request, "ເກີດຂໍ້ຜິດພາດໃນການอັບເດດໃບສັ່ງຊື້")

        items_formset = self._create_items_formset(data=request.POST)
        context = self._get_context_data(form, items_formset)
        return render(request, self.template_name, context)

    def _get_employee(self, user):
        try:
            return EmployeesModel.objects.get(user=user)
        except EmployeesModel.DoesNotExist:
            logger.error(f"Employee not found for user {user.id}")
            raise ValueError(f"Employee profile not found for user {user.username}")


    def get_context_data(self, **kwargs):
        """Additional context data method for potential future use."""
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}
        context.update({
            'po': self.po,
            'invoice': self.invoice,
            'quotation': self.quotation,
            'customer': self.customer,   # 👈 make sure customer available
            'is_update': True,
        })
        return context


@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class OnePoDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = PurchaseOrderModel
    template_name = 'app_po/components/po_view_form.html'
    context_object_name = 'generate_po_form'

    def get_object(self, queryset = None):
        po_id = self.kwargs.get('po_id')
        return get_object_or_404(PurchaseOrderModel, po_id=po_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = {
            'title':f'ລາຍລະອຽດໃບສັ່ງຊື້ {self.kwargs.get("po_id")}',
            'generate_po_form': self.get_object(),
            'employee': getattr(self.request.user, 'employee', None),
        }
        return context

    
# Generate PO PDF with Signature
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class GeneratePoPdfView(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_po/components/po_pdf_generator.html'

    def get(self, request, *args, **kwargs):
        po_id = self.kwargs.get('po_id')
        po = get_object_or_404(PurchaseOrderModel, po_id=po_id)

        context = {
            'generate_po_form':po,
            'employee': getattr(self.request.user, 'employee', None),
            'STATIC_ROOT': settings.STATIC_ROOT
        }
        # Render HTML Content
        html_string = render_to_string(self.template_name, context)

        # Create HTTP Response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="po_{po_id}.pdf'

        # Generate PDF Using weasyprint
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        html.write_pdf(response)
        return response
