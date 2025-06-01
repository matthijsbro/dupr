# tracker/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import LogEntry, UserActivity, ActivityDefinition, ActivityType

class UserActivityChoiceField(forms.ModelChoiceField):
    """Custom field to display user activities nicely in dropdowns."""
    def label_from_instance(self, obj):
        return obj.get_display_name()

class LogEntryForm(forms.ModelForm):
    # Field to select which activity the user is logging for
    user_activity = UserActivityChoiceField(queryset=UserActivity.objects.none()) # Queryset set in __init__

    class Meta:
        model = LogEntry
        fields = ['user_activity', 'quantity_submitted', 'entry_date', 'notes']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date'}), # Use HTML5 date picker
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Get the user from the view kwargs
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Filter the activity dropdown to only show the current user's active activities
            self.fields['user_activity'].queryset = UserActivity.objects.filter(
                user=user, is_active=True
            ).select_related('definition', 'activity_type') # Optimize query
            self.fields['user_activity'].label = _("Activity") # Set label here

        # Add dynamic labels/help text based on selected activity if needed (more advanced, requires JS or HTMX)
        # For now, keep it simple. The unit is implied by the activity name.

        self.fields['quantity_submitted'].label = _("Quantity")
        self.fields['entry_date'].label = _("Date")

class PredefinedActivitySelectForm(forms.Form):
    """Form for selecting a predefined activity to start tracking."""
    definition = forms.ModelChoiceField(
        queryset=ActivityDefinition.objects.filter(is_active=True), # Show only active ones
        label=_("Select Predefined Activity"),
        widget=forms.Select(attrs={'class': 'form-select'}), # Basic select widget
        help_text=_("Choose an activity set up by the site admin.")
    )

    # We add a hidden field to potentially group these additions later if needed
    # Or you could filter the queryset based on the type if necessary