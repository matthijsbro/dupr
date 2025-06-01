# tracker/views.py
from django.shortcuts import redirect, render # Added render for form_invalid example
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, F, Value, IntegerField, ExpressionWrapper, DurationField
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _ # <--- IMPORT ADDED HERE

from .models import LogEntry, UserActivity, PracticeDefinition
from .forms import LogEntryForm, PracticeSelectForm

# --- Mixin for Ownership Check ---

class UserOwnsObjectMixin(UserPassesTestMixin):
    raise_exception = True
    def test_func(self):
        obj = self.get_object()
        return obj.user == self.request.user

# --- Core Views ---

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        user_activities = UserActivity.objects.filter(
            user=user, is_active=True
        ).select_related('definition')

        activity_summary_data = []
        for ua in user_activities:
            logs = LogEntry.objects.filter(user_activity=ua)
            
            total_malas_submitted = logs.aggregate(
                total_malas=Coalesce(Sum('malas_submitted'), 0, output_field=IntegerField())
            )['total_malas']
            
            total_mantras = total_malas_submitted * 108

            total_hours = logs.aggregate(
                total_h=Coalesce(Sum('time_submitted_hours'), 0, output_field=IntegerField())
            )['total_h']
            total_minutes_from_min_field = logs.aggregate(
                total_m=Coalesce(Sum('time_submitted_minutes'), 0, output_field=IntegerField())
            )['total_m']
            
            grand_total_minutes = (total_hours * 60) + total_minutes_from_min_field
            
            display_total_hours = grand_total_minutes // 60
            display_total_minutes = grand_total_minutes % 60

            activity_summary_data.append({
                'user_activity': ua,
                'display_name': ua.get_display_name(),
                'practice_type': ua.definition.get_practice_type_display(), # Corrected to access definition
                'total_malas_submitted': total_malas_submitted,
                'total_mantras': total_mantras,
                'total_practice_hours': display_total_hours,
                'total_practice_minutes': display_total_minutes,
                'has_entries': logs.exists()
            })
            
        recent_entries = LogEntry.objects.filter(
            user=user
        ).select_related(
            'user_activity',
            'user_activity__definition',
        ).order_by('-entry_date', '-created_at')[:10]

        log_entry_form = LogEntryForm(user=user)
        
        tracked_definition_ids = user_activities.filter(definition__isnull=False).values_list('definition_id', flat=True)
        practice_select_form = PracticeSelectForm()
        practice_select_form.fields['definition'].queryset = PracticeDefinition.objects.filter(
            is_active=True
        ).exclude(pk__in=tracked_definition_ids)

        context['activity_summaries'] = activity_summary_data
        context['recent_entries'] = recent_entries
        context['log_entry_form'] = log_entry_form
        context['practice_select_form'] = practice_select_form
        context['tracked_practices'] = user_activities
        return context

class LogEntryCreateView(LoginRequiredMixin, CreateView):
    model = LogEntry
    form_class = LogEntryForm
    template_name = 'tracker/logentry_form.html'
    success_url = reverse_lazy('tracker:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # form.instance.user = self.request.user # User is set in model's save method via user_activity
        messages.success(self.request, _("Log entry added successfully!"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        # Option 1: Render the dedicated form page with errors (current behavior)
        # return super().form_invalid(form)

        # Option 2: Re-render the dashboard with the invalid form
        # This provides a more integrated UX if the form is primarily on the dashboard.
        dashboard_view = DashboardView()
        dashboard_view.request = self.request # Set request for DashboardView's context
        context = dashboard_view.get_context_data()
        context['log_entry_form'] = form # Substitute the invalid form
        return render(self.request, dashboard_view.template_name, context)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Add Log Entry")
        return context

class LogEntryUpdateView(LoginRequiredMixin, UserOwnsObjectMixin, UpdateView):
    model = LogEntry
    form_class = LogEntryForm
    template_name = 'tracker/logentry_form.html'
    success_url = reverse_lazy('tracker:logentry-history')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Log entry updated successfully!"))
        return super().form_valid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Edit Log Entry")
        return context

class LogEntryDeleteView(LoginRequiredMixin, UserOwnsObjectMixin, DeleteView):
    model = LogEntry
    template_name = 'tracker/logentry_confirm_delete.html'
    success_url = reverse_lazy('tracker:logentry-history')

    def form_valid(self, form):
        messages.success(self.request, _(f"Log entry for '{self.object.user_activity.get_display_name()}' on {self.object.entry_date} deleted."))
        return super().form_valid(form) # Calls self.object.delete()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Confirm Delete Log Entry")
        return context

class LogEntryHistoryView(LoginRequiredMixin, ListView):
    model = LogEntry
    template_name = 'tracker/logentry_history.html'
    context_object_name = 'log_entries'
    paginate_by = 20

    def get_queryset(self):
        return LogEntry.objects.filter(
            user=self.request.user
        ).select_related(
            'user_activity',
            'user_activity__definition'
        ).order_by('-entry_date', '-created_at')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Log Entry History")
        return context

class UserActivityAddPracticeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = PracticeSelectForm(request.POST)
        user = request.user

        tracked_definition_ids = UserActivity.objects.filter(user=user, definition__isnull=False).values_list('definition_id', flat=True)
        form.fields['definition'].queryset = PracticeDefinition.objects.filter(is_active=True).exclude(pk__in=tracked_definition_ids)

        if form.is_valid():
            definition = form.cleaned_data['definition']
            try:
                UserActivity.objects.create(
                    user=user,
                    definition=definition,
                    is_active=True
                )
                messages.success(request, _(f"Started tracking '{definition.name}'. You can now add log entries for it."))
            except IntegrityError: # Handles the unique_together constraint
                messages.warning(request, _(f"You are already tracking '{definition.name}'."))
            except Exception as e: # Catch any other unexpected error
                messages.error(request, _(f"An unexpected error occurred: {e}"))
        else:
            # Collect form errors to display them
            error_message_list = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_message_list.append(f"{form.fields[field].label if field != '__all__' else ''}: {error}")
            if not error_message_list and form.non_field_errors():
                 for error in form.non_field_errors():
                    error_message_list.append(str(error))
            
            if not error_message_list: # Fallback generic message
                 error_message_list.append(_("Invalid selection. Please choose from the list."))

            messages.error(request, " ".join(error_message_list))
        
        return HttpResponseRedirect(reverse_lazy('tracker:dashboard'))