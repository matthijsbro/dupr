# tracker/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import LogEntry, UserActivity, PracticeDefinition

class UserActivityChoiceField(forms.ModelChoiceField):
    """Custom field to display user activities nicely in dropdowns."""
    def label_from_instance(self, obj):
        # UserActivity now gets its display name from the linked PracticeDefinition
        return obj.get_display_name()

class LogEntryForm(forms.ModelForm):
    user_activity = UserActivityChoiceField(
        queryset=UserActivity.objects.none(),
        label=_("Practice to Log For")
    )
    malas_submitted = forms.IntegerField(
        required=False, 
        min_value=0,
        label=_("Malas Completed"),
        widget=forms.NumberInput(attrs={'placeholder': _('e.g., 10')})
    )
    time_submitted_hours = forms.IntegerField(
        required=False, 
        min_value=0, 
        label=_("Practice Time (Hours)"),
        widget=forms.NumberInput(attrs={'placeholder': _('e.g., 1')})
    )
    time_submitted_minutes = forms.IntegerField(
        required=False, 
        min_value=0, max_value=59, 
        label=_("Practice Time (Minutes)"),
        widget=forms.NumberInput(attrs={'placeholder': _('e.g., 30')})
    )

    class Meta:
        model = LogEntry
        fields = [
            'user_activity', 
            'malas_submitted', 
            'time_submitted_hours', 
            'time_submitted_minutes', 
            'entry_date', 
            'notes'
        ]
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['user_activity'].queryset = UserActivity.objects.filter(
                user=user, is_active=True
            ).select_related('definition') # Optimize query

        # Set initial values to None if instance is not provided (CreateView)
        # to make placeholders visible and avoid "0" appearing initially.
        if not self.instance or not self.instance.pk:
            self.fields['malas_submitted'].initial = None
            self.fields['time_submitted_hours'].initial = None
            self.fields['time_submitted_minutes'].initial = None


    def clean(self):
        cleaned_data = super().clean()
        malas = cleaned_data.get('malas_submitted')
        hours = cleaned_data.get('time_submitted_hours')
        minutes = cleaned_data.get('time_submitted_minutes')

        # If all are None or 0 (after being defaulted by model's PositiveIntegerField)
        has_malas = malas is not None and malas > 0
        has_hours = hours is not None and hours > 0
        has_minutes = minutes is not None and minutes > 0
        
        if not (has_malas or has_hours or has_minutes):
            raise forms.ValidationError(
                _("Please enter a value for Malas, or Time (Hours/Minutes), or both."),
                code='no_data_submitted'
            )
        
        # Ensure minutes are within 0-59 (already handled by model validator but good for form too)
        if minutes is not None and (minutes < 0 or minutes > 59):
            self.add_error('time_submitted_minutes', _("Minutes must be between 0 and 59."))

        # If one part of time is entered, the other should default to 0 if blank,
        # or ensure they are treated as a pair.
        if (hours is not None and hours > 0) and minutes is None:
            cleaned_data['time_submitted_minutes'] = 0
        if (minutes is not None and minutes > 0) and hours is None:
            cleaned_data['time_submitted_hours'] = 0
        
        # If only one is None after potential defaults, make both None if the other is also 0
        # This handles the case where a user might clear one field.
        if hours == 0 and minutes == 0:
             if malas is None or malas == 0: # only if no malas either
                pass # Already caught by the no_data_submitted validation
        elif hours is None and minutes is None and (malas is None or malas == 0) :
             pass # Already caught

        return cleaned_data


class PracticeSelectForm(forms.Form):
    """Form for selecting a predefined practice to start tracking."""
    definition = forms.ModelChoiceField(
        queryset=PracticeDefinition.objects.filter(is_active=True),
        label=_("Select Practice to Track"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_("Choose a practice set up by the site admin.")
    )