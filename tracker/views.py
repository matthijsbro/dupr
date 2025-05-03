# tracker/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, F # F object allows referencing model fields in queries
from django.contrib import messages # To provide feedback to the user
from django.db import IntegrityError # To catch duplicate entries
from django.views import View # Import generic View
from django.http import HttpResponseRedirect

from .models import LogEntry, UserActivity, ActivityDefinition, ActivityType
from .forms import LogEntryForm, UserActivityCreateForm, PredefinedActivitySelectForm

# --- Mixin for Ownership Check ---

class UserOwnsObjectMixin(UserPassesTestMixin):
    """
    Mixin to ensure the logged-in user owns the object being accessed.
    Assumes the object has a 'user' ForeignKey field.
    """
    raise_exception = True # Raise Forbidden (403) if test fails

    def test_func(self):
        obj = self.get_object()
        return obj.user == self.request.user

# --- Core Views ---

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Displays the main tracker dashboard for the logged-in user.
    Shows summaries, recent entries, and forms to add data.
    """
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's active tracked activities
        user_activities = UserActivity.objects.filter(
            user=user, is_active=True
        ).select_related('definition', 'activity_type') # Optimize query

        # Calculate totals per activity
        activity_totals = user_activities.annotate(
            total_quantity=Sum('log_entries__quantity_submitted'),
            total_calculated=Sum('log_entries__calculated_total')
        ).order_by('activity_type__name', 'definition__name', 'custom_name')

        # Get recent log entries
        recent_entries = LogEntry.objects.filter(
            user=user
        ).select_related( # Optimize query
            'user_activity',
            'user_activity__definition',
            'user_activity__activity_type'
        ).order_by('-entry_date', '-created_at')[:10] # Show last 10

        # Prepare forms
        log_entry_form = LogEntryForm(user=user) # Pass user to filter activity choices
        user_activity_create_form = UserActivityCreateForm()
 # Filter out definitions the user ALREADY tracks
        tracked_definition_ids = user_activities.filter(definition__isnull=False).values_list('definition_id', flat=True)
        predefined_activity_select_form = PredefinedActivitySelectForm()
        predefined_activity_select_form.fields['definition'].queryset = ActivityDefinition.objects.filter(
            is_active=True
        ).exclude(
            pk__in=tracked_definition_ids # Don't show activities already tracked
        )

        context['activity_totals'] = activity_totals
        context['recent_entries'] = recent_entries
        context['log_entry_form'] = log_entry_form
        context['user_activity_create_form'] = user_activity_create_form
        context['predefined_activity_select_form'] = predefined_activity_select_form
        context['tracked_activities'] = user_activities # List of activities user is tracking

        return context

class LogEntryCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new log entry.
    """
    model = LogEntry
    form_class = LogEntryForm
    template_name = 'tracker/logentry_form.html' # Re-use form template
    success_url = reverse_lazy('tracker:dashboard') # Redirect to dashboard after success

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the user for the log entry before saving."""
        # The user is already implicitly set via the UserActivity's user
        # but we can double-check or explicitly set if needed based on model logic.
        # The save method in the LogEntry model handles setting the user field.
        messages.success(self.request, "Log entry added successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        # Need to render the dashboard template again with the invalid form
        # This is tricky with CreateView. Often better to handle form processing
        # directly in the DashboardView for a smoother UX if form is on dashboard.
        # Alternatively, redirect back to dashboard with error message,
        # or use a dedicated page for adding entries.
        # For now, let CreateView render its default error page (logentry_form.html)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context if needed, e.g., page title."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Add Log Entry"
        return context


class LogEntryUpdateView(LoginRequiredMixin, UserOwnsObjectMixin, UpdateView):
    """
    View for editing an existing log entry. Ensures user owns the entry.
    """
    model = LogEntry
    form_class = LogEntryForm
    template_name = 'tracker/logentry_form.html' # Re-use form template
    success_url = reverse_lazy('tracker:logentry-history') # Redirect to history after success

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Log entry updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context if needed, e.g., page title."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Edit Log Entry"
        return context


class LogEntryDeleteView(LoginRequiredMixin, UserOwnsObjectMixin, DeleteView):
    """
    View for deleting a log entry. Ensures user owns the entry.
    Requires confirmation via POST request.
    """
    model = LogEntry
    template_name = 'tracker/logentry_confirm_delete.html' # Confirmation template
    success_url = reverse_lazy('tracker:logentry-history') # Redirect to history

    def form_valid(self, form):
        messages.success(self.request, f"Log entry for '{self.object.user_activity.get_display_name()}' on {self.object.entry_date} deleted.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add extra context if needed, e.g., page title."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Confirm Delete Log Entry"
        return context


class LogEntryHistoryView(LoginRequiredMixin, ListView):
    """
    Displays a paginated list of all log entries for the logged-in user.
    """
    model = LogEntry
    template_name = 'tracker/logentry_history.html'
    context_object_name = 'log_entries'
    paginate_by = 20 # Show 20 entries per page

    def get_queryset(self):
        """Filter entries to only show those belonging to the logged-in user."""
        return LogEntry.objects.filter(
            user=self.request.user
        ).select_related( # Optimize query
            'user_activity',
            'user_activity__definition',
            'user_activity__activity_type'
        ).order_by('-entry_date', '-created_at') # Order by date

    def get_context_data(self, **kwargs):
        """Add extra context if needed, e.g., page title."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Log Entry History"
        return context

# --- Views for Managing User Activities ---

class UserActivityCreateView(LoginRequiredMixin, FormView):
    """
    Allows users to add a new custom activity to their tracking list.
    """
    form_class = UserActivityCreateForm
    template_name = 'tracker/useractivity_form.html' # Dedicated form template
    success_url = reverse_lazy('tracker:dashboard')

    def form_valid(self, form):
        """Create the UserActivity instance."""
        activity_type = form.cleaned_data['activity_type']
        custom_name = form.cleaned_data['custom_name']
        user = self.request.user

        try:
            # Create the UserActivity
            UserActivity.objects.create(
                user=user,
                activity_type=activity_type,
                custom_name=custom_name,
                # definition will be None
                is_active=True
            )
            messages.success(self.request, f"Activity '{custom_name}' added to your tracking list.")
        except IntegrityError:
            # This happens if unique_together constraint fails
            messages.error(self.request, f"You are already tracking an activity named '{custom_name}' of type '{activity_type.name}'.")
            # Return the form with the error instead of redirecting
            return super().form_invalid(form)
        except Exception as e:
            # Catch other potential errors during creation
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return super().form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context if needed, e.g., page title."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Add Custom Activity to Track"
        return context

# --- View for Adding Predefined Activities ---
class UserActivityAddPredefinedView(LoginRequiredMixin, View):
    """Handles the POST request to add a predefined activity."""

    def post(self, request, *args, **kwargs):
        form = PredefinedActivitySelectForm(request.POST)
        user = request.user

        # Re-query the allowed definitions for validation, excluding already tracked ones
        tracked_definition_ids = UserActivity.objects.filter(user=user, definition__isnull=False).values_list('definition_id', flat=True)
        form.fields['definition'].queryset = ActivityDefinition.objects.filter(is_active=True).exclude(pk__in=tracked_definition_ids)

        if form.is_valid():
            definition = form.cleaned_data['definition']
            try:
                # Create the UserActivity linking user and the chosen definition
                UserActivity.objects.create(
                    user=user,
                    definition=definition,
                    activity_type=definition.activity_type, # Get type from definition
                    is_active=True
                )
                messages.success(request, f"Started tracking '{definition.name}'. You can now add log entries for it.")
            except IntegrityError:
                messages.warning(request, f"You are already tracking '{definition.name}'.")
            except Exception as e:
                 messages.error(request, f"An unexpected error occurred: {e}")

        else:
            # If form is invalid (e.g., user manipulated POST data)
            messages.error(request, "Invalid selection. Please choose from the list.")

        # Redirect back to the dashboard regardless of success/failure
        return HttpResponseRedirect(reverse_lazy('tracker:dashboard'))

# --- Optional: Views for listing/archiving UserActivity ---
# class UserActivityListView(LoginRequiredMixin, ListView): ...
# class UserActivityUpdateView(LoginRequiredMixin, UserOwnsObjectMixin, UpdateView): ... # For archiving (setting is_active=False)
