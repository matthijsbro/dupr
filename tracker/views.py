# tracker/views.py
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, F, Value, IntegerField, ExpressionWrapper, DurationField, OuterRef, Subquery, Max
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone # For default date

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

        # Get user's active tracked activities, ordered by most recently logged
        most_recent_log_entry_subquery = LogEntry.objects.filter(
            user_activity=OuterRef('pk')
        ).order_by('-created_at').values('created_at')[:1]

        user_activities = UserActivity.objects.filter(
            user=user, is_active=True
        ).select_related('definition').annotate(
            last_log_created_at=Subquery(most_recent_log_entry_subquery)
        ).order_by(F('last_log_created_at').desc(nulls_last=True), 'definition__name')


        # Determine the practice for the log form:
        # 1. Last explicitly selected (if any, passed via session or GET for e.g. form re-render)
        # 2. Last practice user submitted an entry for
        # 3. First practice in the (now sorted) user_activities list
        selected_practice_for_log = None # Will be set below

        last_log_entry_for_user = LogEntry.objects.filter(user=user).order_by('-created_at').first()
        if last_log_entry_for_user:
            selected_practice_for_log = last_log_entry_for_user.user_activity
        elif user_activities.exists():
            selected_practice_for_log = user_activities.first()

        activity_summary_data = []
        for ua in UserActivity.objects.filter(user=user, is_active=True).select_related('definition').order_by('definition__name'): # Keep original order for summary
            logs = LogEntry.objects.filter(user_activity=ua)
            total_malas_submitted = logs.aggregate(total_malas=Coalesce(Sum('malas_submitted'), 0, output_field=IntegerField()))['total_malas']
            total_mantras = total_malas_submitted * 108
            total_hours = logs.aggregate(total_h=Coalesce(Sum('time_submitted_hours'), 0, output_field=IntegerField()))['total_h']
            total_minutes_from_min_field = logs.aggregate(total_m=Coalesce(Sum('time_submitted_minutes'), 0, output_field=IntegerField()))['total_m']
            grand_total_minutes = (total_hours * 60) + total_minutes_from_min_field
            display_total_hours = grand_total_minutes // 60
            display_total_minutes = grand_total_minutes % 60

            activity_summary_data.append({
                'user_activity': ua,
                'display_name': ua.get_display_name(),
                'practice_type': ua.definition.get_practice_type_display(),
                'total_malas_submitted': total_malas_submitted,
                'total_mantras': total_mantras,
                'total_practice_hours': display_total_hours,
                'total_practice_minutes': display_total_minutes,
                'has_entries': logs.exists()
            })
            
        recent_entries = LogEntry.objects.filter(user=user).select_related(
            'user_activity', 'user_activity__definition'
        ).order_by('-entry_date', '-created_at')[:5]

        initial_log_form_data = {'entry_date': timezone.localdate()} # Default date to today
        if selected_practice_for_log:
            initial_log_form_data['user_activity'] = selected_practice_for_log
        
        log_entry_form = LogEntryForm(user=user, initial=initial_log_form_data)
        
        tracked_definition_ids = user_activities.values_list('definition_id', flat=True)
        practice_select_form = PracticeSelectForm()
        practice_select_form.fields['definition'].queryset = PracticeDefinition.objects.filter(
            is_active=True
        ).exclude(pk__in=tracked_definition_ids)

        context['activity_summaries'] = activity_summary_data
        context['recent_entries'] = recent_entries
        context['log_entry_form'] = log_entry_form
        context['practice_select_form'] = practice_select_form
        context['tracked_practices'] = user_activities # Now ordered by recency for the scroller
        context['selected_practice_for_log'] = selected_practice_for_log

        return context

class LogEntryCreateView(LoginRequiredMixin, CreateView):
    model = LogEntry
    form_class = LogEntryForm
    template_name = 'tracker/logentry_form.html'
    success_url = reverse_lazy('tracker:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        # Set initial practice if available from a POST param (e.g. if form was submitted from dashboard)
        if self.request.method == 'POST' and 'user_activity' in self.request.POST:
             if 'initial' not in kwargs:
                kwargs['initial'] = {}
             try:
                # Ensure user_activity POST value is valid and belongs to user
                user_activity_instance = UserActivity.objects.get(pk=self.request.POST.get('user_activity'), user=self.request.user)
                kwargs['initial']['user_activity'] = user_activity_instance
             except (UserActivity.DoesNotExist, ValueError):
                pass # Let form validation handle if it's truly invalid
        elif 'initial' not in kwargs or 'user_activity' not in kwargs['initial']:
            # Default to last logged or first practice if not in POST
            last_log = LogEntry.objects.filter(user=self.request.user).order_by('-created_at').first()
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            if last_log:
                kwargs['initial']['user_activity'] = last_log.user_activity
            else:
                first_tracked = UserActivity.objects.filter(user=self.request.user, is_active=True).order_by('definition__name').first()
                if first_tracked:
                    kwargs['initial']['user_activity'] = first_tracked
        
        if 'initial' not in kwargs: # Ensure initial exists
            kwargs['initial'] = {}
        if 'entry_date' not in kwargs['initial']: # Default entry_date if not set
            kwargs['initial']['entry_date'] = timezone.localdate()

        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Log entry added successfully!"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        dashboard_view = DashboardView()
        dashboard_view.request = self.request
        context = dashboard_view.get_context_data()
        
        # Preserve submitted form data for re-rendering
        # Create a new form instance with the submitted POST data and user
        error_form = LogEntryForm(self.request.POST, user=self.request.user)
        context['log_entry_form'] = error_form
        
        # Try to set selected_practice_for_log based on what was submitted in the errored form
        submitted_user_activity_id = self.request.POST.get('user_activity')
        if submitted_user_activity_id:
            try:
                context['selected_practice_for_log'] = UserActivity.objects.get(pk=submitted_user_activity_id, user=self.request.user)
            except (UserActivity.DoesNotExist, ValueError):
                 # If invalid ID was submitted, default to what dashboard would normally show
                pass # selected_practice_for_log from get_context_data will be used

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
            error_message_list = []
            for field, errors_list in form.errors.items(): # errors is a list
                for error in errors_list:
                    field_label = form.fields[field].label if field != '__all__' else ''
                    error_message_list.append(f"{field_label}: {error}" if field_label else str(error))
            
            if not error_message_list: # Fallback generic message
                 error_message_list.append(_("Invalid selection. Please choose from the list."))

            messages.error(request, " ".join(error_message_list))
        
        return HttpResponseRedirect(reverse_lazy('tracker:dashboard'))
