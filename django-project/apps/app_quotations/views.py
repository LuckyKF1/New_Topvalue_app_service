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
from django.views.generic import ListView, DetailView, UpdateView,CreateView, FormView, TemplateView, DeleteView, View
#=====[ Third-party Packages ]=====
from django_ratelimit.decorators import ratelimit
from weasyprint import HTML
# from docxtpl import DocxTemplate
import io
#=====[ Django Forms & Formsets ]=====
from django.forms import inlineformset_factory
#=====[ Local App Imports: Forms ]=====
from .forms import (
    QuotationInformationModelForm,
    CustomersModelForm,
    QuotationItemsFormSet,
    AdditionalExpensesFormSet
)
#=====[ Local App Imports: Models ]=====
from .models import QuotationInformationModel, QuotationItemsModel, AdditionalExpensesModel
from apps.app_customers.models import CustomersModel
from apps.app_employee.models import EmployeesModel
# from apps.users.mixins import RoleRequiredMixin


# Class Base Views
#====================================== Home page and list of all quotations ======================================
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class HomeView(LoginRequiredMixin, ListView):
    login_url = 'users:login'
    model = QuotationInformationModel
    template_name = 'app_quotations/home.html'
    context_object_name = 'all_quotations'

    def get_queryset(self):
        queryset = super().get_queryset()
        #Search / Filter Function
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(quotation_id__icontains=search) |
                Q(customer__company_name__icontains=search) |
                Q(customer__contact_person_name__icontains=search)
            )
        # Order by Status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status = status)
        
        # Order by monthly
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        if start_date and end_date:
            queryset = queryset.filter(start_date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        # Default order by
        queryset = queryset.order_by('-end_date')
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['title'] = 'ລາຍການໃບສະເຫນີລາຄາ'
        context['status_list'] = QuotationInformationModel.Status.choices
        return context


# # ModelFormMixins + View
# @method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
# class QuotationCreateUpdateView(LoginRequiredMixin, View):
#     login_url = 'users:login'
#     template_name = 'app_quotations/create_quotation.html'

#     def get_object(self):
#         quotation_id = self.kwargs.get('quotation_id')
#         if quotation_id:
#             return get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)
#         return None

#     def get(self, request, *args, **kwargs):
#         obj = self.get_object()
#         context = self.get_context_data(obj=obj)
#         return render(request, self.template_name, context)

#     def post(self, request, *args, **kwargs):
#         obj = self.get_object()
#         context = self.get_context_data(obj=obj, post_data=request.POST)
#         if self.forms_valid(context):
#             return redirect(self.get_success_url(context['quotation_form'].instance))
#         return render(request, self.template_name, context)

#     def get_context_data(self, obj=None, post_data=None):
#         context = {}
#         context['title'] = 'ແກ້ໄຂໃບສະເຫນີລາຄາ' if obj else 'ສ້າງໃບສະເຫນີລາຄາ'

#         if post_data:
#             context['quotation_form'] = QuotationInformationModelForm(post_data, instance=obj)
#             context['customer_form'] = CustomersModelForm(post_data, instance=obj.customer if obj else None)
#             context['items_formset'] = QuotationItemsFormSet(post_data, instance=obj, prefix='items')
#             context['additional_formset'] = AdditionalExpensesFormSet(post_data, instance=obj, prefix='additional')
#         else:
#             context['quotation_form'] = QuotationInformationModelForm(instance=obj)
#             context['customer_form'] = CustomersModelForm(instance=obj.customer if obj else None)
#             context['items_formset'] = QuotationItemsFormSet(instance=obj, prefix='items')
#             context['additional_formset'] = AdditionalExpensesFormSet(instance=obj, prefix='additional')
#         return context

#     def forms_valid(self, context):
#         quo_form = context['quotation_form']
#         cus_form = context['customer_form']
#         item_formset = context['items_formset']
#         additional_formset = context['additional_formset']

#         if all([quo_form.is_valid(), cus_form.is_valid(), item_formset.is_valid(), additional_formset.is_valid()]):
#             with transaction.atomic():
#                 customer = cus_form.save()
#                 quotation = quo_form.save(commit=False)
#                 quotation.customer = customer
#                 if not quotation.pk:  # Create
#                     quotation.created_by = self.request.user.employee
#                 quotation.save()

#                 item_formset.instance = quotation
#                 item_formset.save()

#                 additional_formset.instance = quotation
#                 additional_formset.save()
#             return True
#         return False

#     def get_success_url(self, obj):
#         return reverse_lazy(
#             'app_quotations:quotation_details',
#             kwargs={'quotation_id': obj.quotation_id}
#         )
                
    
# Create Quotation
@method_decorator(
    ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), 
    name='dispatch'
)
class CreateQuotationView(LoginRequiredMixin, CreateView):
    login_url = 'users:login'
    model = QuotationInformationModel
    form_class = QuotationInformationModelForm
    template_name = 'app_quotations/create_quotation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ສ້າງໃບສະເຫນີລາຄາໃຫມ່'

        if self.request.method == 'POST':
            context['form'] = self.get_form()
            context['customer_form'] = CustomersModelForm(self.request.POST)
            context['items_formset'] = QuotationItemsFormSet(self.request.POST, prefix='items')
            context['additional_formset'] = AdditionalExpensesFormSet(self.request.POST, prefix='additional')
        else:
            context['form'] = self.get_form()
            context['customer_form'] = CustomersModelForm()
            context['items_formset'] = QuotationItemsFormSet(prefix='items')
            context['additional_formset'] = AdditionalExpensesFormSet(prefix='additional')
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        customer_form = context['customer_form']
        items_formset = context['items_formset']
        additional_formset = context['additional_formset']

        if customer_form.is_valid() and items_formset.is_valid() and additional_formset.is_valid():
            with transaction.atomic():
                customer = customer_form.save()

                self.object = form.save(commit=False)
                self.object.customer = customer
                self.object.created_by = getattr(self.request.user, "employee", None)
                self.object.save()

                items_formset.instance = self.object
                items_formset.save()

                additional_formset.instance = self.object
                additional_formset.save()
            return redirect(self.get_success_url())
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
    
    def get_success_url(self):
        return reverse_lazy(
            'app_quotations:quotation_details',
            kwargs={'quotation_id': self.object.quotation_id},
        )



# Update View
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class UpdateView(LoginRequiredMixin, UpdateView):
    login_url = 'users:login'
    model = QuotationInformationModel
    form_class = QuotationInformationModelForm
    template_name = 'app_quotations/create_quotation.html'
    slug_field = 'quotation_id'
    slug_url_kwarg = 'quotation_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ແກ້ໄຂໃບສະເຫນີລາຄາ'

        if self.request.method == 'POST':
            context['form'] = self.get_form_class()(
                self.request.POST,
                self.request.FILES,
                instance = self.object
            )
            context['customer_form'] = CustomersModelForm(self.request.POST, instance=self.object.customer)
            context['items_formset'] = QuotationItemsFormSet(self.request.POST, instance=self.object, prefix='items')
            context['additional_formset'] = AdditionalExpensesFormSet(self.request.POST, instance=self.object, prefix='additional')
        else:
            context['customer_form'] = CustomersModelForm(instance=self.object.customer)
            context['items_formset'] = QuotationItemsFormSet(instance=self.object, prefix='items')
            context['additional_formset'] = AdditionalExpensesFormSet(instance=self.object, prefix='additional')
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        customer_form = context['customer_form']
        items_formset = context['items_formset']
        additional_formset = context['additional_formset']

        if customer_form.is_valid() and items_formset.is_valid() and additional_formset.is_valid():
            with transaction.atomic():
                customer = customer_form.save()
                self.object = form.save(commit=False)
                self.object.customer = customer
                self.object.save()

                items_formset.instance = self.object
                items_formset.save()

                additional_formset.instance = self.object
                additional_formset.save()
            return redirect(self.get_success_url())
        return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy(
            'app_quotations:quotation_details',
            kwargs={
                'quotation_id':self.object.quotation_id
            }
        )
    
# DeleteView
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class DeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'users:login'
    model = QuotationInformationModel
    template_name = 'app_quotations/components/delete_quotation.html'
    context_object_name = 'delete_one_quotation'
    slug_field = 'quotation_id'
    slug_url_kwarg = 'quotation_id'
    success_url = reverse_lazy('app_quotations:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ລຶບໃບສະເຫນີລາຄານີ້'
        return context
    


# Quotation Details
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class QuotationDetailView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = QuotationInformationModel
    template_name = 'app_quotations/quotation_details.html'
    context_object_name = 'quotation'
    slug_field = 'quotation_id'
    slug_url_kwarg = 'quotation_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quotation = self.object

        # Related objects
        quotation_items = quotation.items.all()
        additional_expenses_qs = quotation.additional_payments.all()  # QuerySet

        additional_expense = additional_expenses_qs.first() if additional_expenses_qs.exists() else None

        # Calculate totals
        total_price = quotation.total_all_products or 0
        it_service_amount = additional_expense.it_service_output if additional_expense else 0
        vat_amount = additional_expense.vat_output if additional_expense else 0
        grand_total = additional_expense.grand_total if additional_expense else total_price

        # Update context
        context.update({
            'title': 'ລາຍລະອຽດຂອງໃບສະເຫນີລາຄາ',
            'one_quotation': quotation,
            'quotation_items': quotation_items,
            'additional_expense': additional_expense,
            'total_price': total_price,
            'it_service_amount': it_service_amount,
            'vat_amount': vat_amount,
            'grand_total': grand_total,
        })
        return context


# Details of One Quotation
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class OneQuotationDetailsView(LoginRequiredMixin, DetailView):
    login_url = 'users:login'
    model = QuotationInformationModel
    template_name = 'app_quotations/components/quotation_form.html'
    context_object_name = 'generate_quotation_form'
    
    def get_object(self, queryset=None):
        quotation_id = self.kwargs.get('quotation_id')
        return get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ໃບສະເຫນີລາຄາ'
        context['employee'] = getattr(self.request.user, 'employee', None)
        return context
    

# Generate quotation pdf with weasyprint
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class GenerateQuotationPDF(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_quotations/components/quotation_pdf_generator.html'

    def get(self, request, *args, **kwargs):
        # Get Quotation Object
        quotation_id = kwargs.get('quotation_id')
        quotation = get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)

        #Get Context
        context = {
            'generate_quotation_form':quotation,
            'employee':getattr(request.user, 'employee', None),
            'STATIC_ROOT':settings.STATIC_ROOT,
        }
        # Render HTML Content
        html_string = render_to_string(self.template_name, context)

        # Create HTTP Response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quotation_{quotation_id}.pdf"'

        # Generate PDF Using weasyprint
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        html.write_pdf(response)
        return response
    

# Generate Quotation pdf without signature 
@method_decorator(ratelimit(key='header:X-Forwarded-For', rate=settings.RATE_LIMIT, block=True), name='dispatch')
class GenerateQuotationPDFNoSig(LoginRequiredMixin, View):
    login_url = 'users:login'
    template_name = 'app_quotations/components/quotation_pdf_generator_no_sig.html'

    def get(self, request, *args, **kwargs):
        quotation_id = kwargs.get('quotation_id')
        quotation = get_object_or_404(QuotationInformationModel, quotation_id=quotation_id)

        # context สำหรับ template
        context = {
            'generate_quotation_form': quotation,
        }

        # render template เป็น html string
        html_string = render_to_string(self.template_name, context)

        # prepare response pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quotation_{quotation_id}.pdf"'

        # generate pdf จาก html
        HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)

        return response
    