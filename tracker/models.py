# tracker/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from modelcluster.models import ClusterableModel # If using ParentalKey below, otherwise not needed now
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet

# --- Admin Managed Definitions (Snippets) ---

@register_snippet
class ActivityType(models.Model):
    """
    Broad categories for activities (e.g., 'Accumulations', 'Daily Habits').
    Managed by Admins via Snippets UI.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text=_("A unique identifier used in URLs and code."))
    description = models.TextField(blank=True)
    # Removed: allow_user_defined_activities field

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('description'),
        # Removed: FieldPanel('allow_user_defined_activities'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Activity Type")
        verbose_name_plural = _("Activity Types")
        ordering = ['name']

@register_snippet
class ActivityDefinition(models.Model):
    """
    Specific activities predefined by Admins (e.g., 'Chenrezig Mantra').
    Managed by Admins via Snippets UI.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, help_text=_("A unique identifier used in URLs and code."))
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.PROTECT, # Prevent deleting a type if activities use it
        related_name='activity_definitions'
    )
    unit_name = models.CharField(
        max_length=50,
        default="repetitions", # Flexible default
        help_text=_("The name of the unit being counted (e.g., 'malas', 'mantras', 'minutes', 'sessions').")
    )
    unit_multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text=_("Factor to convert submitted quantity to a base value (e.g., 108 for malas converting to mantras). Use 1 if no conversion needed.")
    )
    is_active = models.BooleanField(default=True, help_text=_("Uncheck to hide this from users selecting new activities."))

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('activity_type'),
        FieldPanel('unit_name'),
        FieldPanel('unit_multiplier'),
        FieldPanel('is_active'),
    ]

    def __str__(self):
        return f"{self.name} ({self.activity_type.name})"

    class Meta:
        verbose_name = _("Predefined Activity")
        verbose_name_plural = _("Predefined Activities")
        ordering = ['activity_type', 'name']


# --- User Specific Data (Standard Django Models) ---

class UserActivity(models.Model):
    """
    Represents an activity a specific user is tracking.
    Can link to a Predefined Activity OR be a custom one defined by the user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tracked_activities',
        verbose_name=_("User")
    )
    # Link to an admin-defined activity (optional)
    definition = models.ForeignKey(
        ActivityDefinition,
        on_delete=models.SET_NULL, # Keep tracking even if admin deletes definition? Or PROTECT? Discuss. SET_NULL allows history retention.
        null=True, blank=True,
        related_name='user_trackers',
        verbose_name=_("Predefined Activity")
    )
    # Removed: custom_name field
    # custom_name = models.CharField(
    #     max_length=255,
    #     blank=True,
    #     verbose_name=_("Custom Activity Name")
    # )
    
    # Must know the type, especially if definition is null
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.PROTECT, # Protect the type
        related_name='user_activities',
        verbose_name=_("Activity Type")
    )
    is_active = models.BooleanField(default=True, help_text=_("User can archive activities they no longer track."))
    created_at = models.DateTimeField(auto_now_add=True)

    # Ensure either definition is set OR (custom_name AND activity_type allows user defined)
    def clean(self):
        if not self.definition:
            # Now that custom_name is removed, a UserActivity MUST have a definition
            raise ValidationError(_("A User Activity must be linked to a predefined activity."))
        # If definition is set, ensure activity_type matches definition's type
        if self.definition and self.definition.activity_type != self.activity_type:
            raise ValidationError(_("Activity type must match the predefined activity's type."))

    def get_display_name(self):
        # Now relies solely on definition.name
        if self.definition:
            return self.definition.name
        return _("N/A (Error: No definition)") # Should not happen if clean() works

    def get_unit_name(self):
        # Now relies solely on definition.unit_name
        if self.definition:
            return self.definition.unit_name
        return _("quantity") # Fallback, though should not be needed

    def get_unit_multiplier(self):
        # Now relies solely on definition.unit_multiplier
        if self.definition:
            return self.definition.unit_multiplier
        return 1 # Fallback, though should not be needed

    def __str__(self):
        return f"{self.user.username} - {self.get_display_name()}"

    class Meta:
        verbose_name = _("User Tracked Activity")
        verbose_name_plural = _("User Tracked Activities")
        # Prevent user from tracking the exact same predefined activity twice
        unique_together = [['user', 'definition']] # Removed custom_name from unique_together
        ordering = ['user', 'activity_type', 'definition__name'] # Removed custom_name from ordering


class LogEntry(models.Model):
    """
    A single submission/entry by a user for a tracked activity.
    """
    user_activity = models.ForeignKey(
        UserActivity,
        on_delete=models.CASCADE, # If the user stops tracking, entries are deleted. Or SET_NULL? Cascade seems logical.
        related_name='log_entries',
        verbose_name=_("Tracked Activity")
    )
    # Denormalize user for easier filtering/permission checks
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='log_entries',
        verbose_name=_("User")
    )
    # Quantity submitted in the activity's unit (e.g., 5 malas)
    quantity_submitted = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Quantity Submitted")
    )
    # Calculated total in base units (e.g., 5 * 108 = 540 mantras)
    calculated_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        editable=False, # Calculated automatically
        verbose_name=_("Calculated Total")
    )
    entry_date = models.DateField(default=timezone.now, verbose_name=_("Date of Activity"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure user consistency
        if self.user_activity:
            self.user = self.user_activity.user
        # Calculate the total
        self.calculated_total = self.quantity_submitted * self.user_activity.get_unit_multiplier()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.user_activity.get_display_name()} - {self.quantity_submitted} {self.user_activity.get_unit_name()} on {self.entry_date}"

    class Meta:
        verbose_name = _("Log Entry")
        verbose_name_plural = _("Log Entries")
        ordering = ['-entry_date', '-created_at'] # Show most recent first