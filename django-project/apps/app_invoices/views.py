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
from .signals import generate_invoice_number
from .models import InvoiceModel
from .forms import InvoiceModelForm
from apps.app_quotations.models import QuotationInformationModel
from apps.app_employee.models import EmployeesModel



# Class Base Views
# Home
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class InvoiceListView(LoginRequiredMixin, ListView):
    login_url = 'users:login'
    model = InvoiceModel
    template_name = 'app_invoices/home.html'
    context_object_name = 'all_invoices'

    #Search / Filter Function
    def get_queryset(self):
        queryset = super().get_queryset()
        # Search 
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(invoice_id__icontains=search) |
                Q(quotation__customer__company_name__icontains=search) |
                Q(quotation__customer__contact_person_name__icontains=search) |
                Q(quotation__quotation_id__icontains=search)
            )
        # Order by Status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Order by Monthly
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')

        if start_date and end_date:
            queryset = queryset.filter(issue_date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(issue_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(issue_date__lte=end_date)

        # Default Order by
        queryset = queryset.order_by('-issue_date')

        # Return Queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['title'] = 'ລາຍການໃບເກັບເງິນທັງຫມົດ'
        context['status_list'] = InvoiceModel.InvoiceStatus.choices
        return context

# Create and Update from app quotations 
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), 
    name='dispatch'
)
class CreateInvoice(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_invoices/create_invoice.html'

    def get(self, request, *args, **kwargs):
        quotation_id = kwargs.get('invoice_id')
        quotation = get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)
        additional_expense = quotation.additional_payments.first()

        form = InvoiceModelForm(
            initial={
                'quotation': quotation,
                'issue_date': quotation.start_date,
                'due_date': quotation.end_date
            }
        )
        context = {
            'form': form,
            'quotation': quotation,
            'additional_expense': additional_expense,
            'title': 'ອອກໃບເກັບເງິນ'
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        quotation_id = kwargs.get('invoice_id')
        quotation = get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)
        additional_expense = quotation.additional_payments.first()

        form = InvoiceModelForm(request.POST, request.FILES)

        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.quotation = quotation
            employee = EmployeesModel.objects.get(user=request.user)
            invoice.created_by = employee

            # if invoice of quotation existing already
            existing_invoice = InvoiceModel.objects.filter(quotation=quotation).first()

            if existing_invoice and not request.POST.get('confirm_update'):
                # Notification to User
                messages.warning(
                    request, 
                    "ມີໃບເກັບເງິນຂອງໃບສະເຫນີລາຄານີ້ແລ້ວ, ຕ້ອງການອັບເດດຫລືບໍ່?"
                )
                context = {
                    'form': form,
                    'quotation': quotation,
                    'additional_expense': additional_expense,
                    'title': 'ຢືນຢັນການອັບເດດໃບເກັບເງິນ',
                    'confirm_update': True,
                    'existing_invoice': existing_invoice
                }
                return render(request, self.template_name, context)

            if existing_invoice and request.POST.get('confirm_update'):
                # If confirmed_update invoice
                # Update invoice
                existing_invoice.issue_date = invoice.issue_date
                existing_invoice.due_date = invoice.due_date
                existing_invoice.created_by = invoice.created_by
                
                if invoice.invoice_signatured:
                    existing_invoice.invoice_signatured = invoice.invoice_signatured

                if invoice.customer_payment:
                    existing_invoice.customer_payment = invoice.customer_payment

                existing_invoice.save()
                invoice = existing_invoice
            else:
                # create new invoice
                invoice.save()
            print("Invoice ID", invoice.invoice_id)
            print("Invoice PK", invoice.pk)
            return redirect('app_invoices:invoice_details', invoice_id=invoice.invoice_id)

        # if form is not valid will be redirect to render
        context = {
            'form': form,
            'quotation': quotation,
            'additional_expense': additional_expense,
            'title': 'ອອກໃບເກັບເງິນ'
        }
        return render(request, self.template_name, context)



# One Invoice Details View
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class InvoiceDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = InvoiceModel
    template_name = 'app_invoices/invoice_details.html'
    context_object_name = 'invoice'
    slug_field = 'invoice_id'
    slug_url_kwarg = 'invoice_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object
        quotation = invoice.quotation

        # Related objects
        items_qs = quotation.items.all()
        additional_expenses_qs = quotation.additional_payments.all()
        additional_expense = additional_expenses_qs.first() if additional_expenses_qs.exists() else None

        # Calculate totals
        total_price = quotation.total_all_products or 0
        it_service_amount = additional_expense.it_service_output if additional_expense else 0
        vat_amount = additional_expense.vat_output if additional_expense else 0
        grand_total = additional_expense.grand_total if additional_expense else total_price

        # Update context
        context.update({
            'title': 'ລາຍລະອຽດຂອງໃບເກັບເງິນ',
            'invoice': invoice,
            'quotation': quotation,
            'items': items_qs,
            'additional_expense': additional_expense,
            'total_price': total_price,
            'it_service_amount': it_service_amount,
            'vat_amount': vat_amount,
            'grand_total': grand_total,
        })
        return context


# Update invoice from invoice details page
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True),
    name='dispatch'
)
class UpdateInvoiceView(LoginRequiredMixin, UpdateView):
    login_url = 'users:login'
    model = InvoiceModel
    form_class = InvoiceModelForm
    template_name = 'app_invoices/create_invoice.html'
    slug_field = 'invoice_id'
    slug_url_kwarg = 'invoice_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        quotation = invoice.quotation

        context.update({
            'title':'ອັບເດດໃບເກັບເງິນ',
            'quotation':quotation,
            'additional_expense':quotation.additional_payments.first(),
        })
        return context
    
    def get_success_url(self):
        messages.success(self.request, 'ອັບເດດໃບເກັບເງິນສຳເລັດ')
        return reverse_lazy(
            'app_invoices:invoice_details',
            kwargs = {
                'invoice_id':self.object.invoice_id
            }
        )
    
    def form_valid(self, form):
        invoice = form.save(commit=False)
        invoice.created_by = EmployeesModel.objects.get(user=self.request.user)
        return super().form_valid(form)

# Delete Invoice
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), 
    name='dispatch'
)
class DeleteInvoiceView(LoginRequiredMixin, DeleteView):
    login_url = 'users:login'
    model = InvoiceModel
    template_name = 'app_invoices/components/delete.html'
    success_url = reverse_lazy('app_invoices:home')
    get_context_data = 'delete_invoice'
    slug_field = 'invoice_id'
    slug_url_kwarg = 'invoice_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"ລົບໃບເກັບເງິນ {self.kwargs['invoice_id']}"
        return context
    
# invoice detials form 
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), 
    name='dispatch'
)
class OneInvoiceDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = InvoiceModel
    template_name = 'app_invoices/components/invoice_view_form.html'
    context_object_name = 'generate_invoice_form'

    def get_object(self, queryset=None):
        invoice_id = self.kwargs.get('invoice_id')
        return get_object_or_404(InvoiceModel, invoice_id=invoice_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ໃບເກັບເງິນ'
        context['employee'] = getattr(self.request.user, 'employee', None)
        context['quotation'] = self.object.quotation
        context['additional_expense'] = self.object.quotation.additional_payments.first()
        return context
    


# Generate Invoice PDF with Signature
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True),
    name='dispatch'
)
class GenerateInvoicePDF(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_invoices/components/invoice_generate_pdf_with_sig.html'

    def get(self, request, *args, **kwargs):
        # Get Invoice Object
        invoice_id = kwargs.get('invoice_id')
        invoice = get_object_or_404(InvoiceModel, invoice_id=invoice_id)

        # Get Context
        context = {
            'generate_invoice_form':invoice,
            'employee':getattr(request.user, 'employee', None),
            'STATIC_ROOT':settings.STATIC_ROOT,
        }
        # Render HTML Content
        html_string = render_to_string(self.template_name, context)

        # Create HTTP response with pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_id}.pdf'

        # Generate pdf using weasyprint
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        html.write_pdf(response)
        return response
    


# Generate Invoice PDF without Signature
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True),
    name='dispatch'
)
class GenerateInvoicePDFNoSig(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_invoices/components/invoice_generate_pdf_without_sig.html'

    def get(self, request, *args, **kwargs):
        # Get Invoice Object
        invoice_id = kwargs.get('invoice_id')
        invoice = get_object_or_404(InvoiceModel, invoice_id=invoice_id)

        # Get Context
        context = {
            'generate_invoice_form':invoice,
        }
        # Render HTML Content
        html_string = render_to_string(self.template_name, context)

        # Create HTTP response with pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_id}.pdf'

        # Generate pdf using weasyprint
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        html.write_pdf(response)
        return response