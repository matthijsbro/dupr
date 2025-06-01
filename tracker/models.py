# tracker/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet

# --- Admin Managed Definitions (Snippets) ---

@register_snippet
class PracticeDefinition(models.Model):
    """
    Specific practices predefined by Admins (e.g., 'Chenrezig Mantra').
    Managed by Admins via Snippets UI.
    """
    PRACTICE_TYPE_CHOICES = [
        ('collective_accumulation', _('Collective Accumulation')),
        ('practice', _('Practice')),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, help_text=_("A unique identifier used in URLs and code."))
    practice_type = models.CharField(
        max_length=50,
        choices=PRACTICE_TYPE_CHOICES,
        default='practice',
        help_text=_("The type of practice.")
    )
    description = models.TextField(blank=True, help_text=_("Optional description of the practice."))
    is_active = models.BooleanField(default=True, help_text=_("Uncheck to hide this from users selecting new practices."))

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('practice_type'),
        FieldPanel('description'),
        FieldPanel('is_active'),
    ]

    def __str__(self):
        return f"{self.name} ({self.get_practice_type_display()})"

    class Meta:
        verbose_name = _("Practice Definition")
        verbose_name_plural = _("Practice Definitions")
        ordering = ['practice_type', 'name']


# --- User Specific Data (Standard Django Models) ---

class UserActivity(models.Model):
    """
    Represents a practice a specific user is tracking.
    Links to a PracticeDefinition.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tracked_activities',
        verbose_name=_("User")
    )
    definition = models.ForeignKey(
        PracticeDefinition,
        on_delete=models.CASCADE, # If admin deletes a practice, remove user's tracking of it.
                                  # Consider PROTECT if you want to prevent deletion if users track it.
        related_name='user_trackers',
        verbose_name=_("Practice Definition")
    )
    is_active = models.BooleanField(default=True, help_text=_("User can archive activities they no longer track."))
    created_at = models.DateTimeField(auto_now_add=True)

    def get_display_name(self):
        return self.definition.name

    def get_practice_type_display(self):
        return self.definition.get_practice_type_display()

    def __str__(self):
        return f"{self.user.username} - {self.get_display_name()}"

    class Meta:
        verbose_name = _("User Tracked Practice")
        verbose_name_plural = _("User Tracked Practices")
        unique_together = [['user', 'definition']]
        ordering = ['user', 'definition__practice_type', 'definition__name']


class LogEntry(models.Model):
    """
    A single submission/entry by a user for a tracked practice.
    Can include Malas, Time, or both.
    """
    user_activity = models.ForeignKey(
        UserActivity,
        on_delete=models.CASCADE,
        related_name='log_entries',
        verbose_name=_("Tracked Practice")
    )
    user = models.ForeignKey( # Denormalized for easier filtering
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='log_entries',
        verbose_name=_("User")
    )
    malas_submitted = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Malas Submitted"),
        help_text=_("Number of malas completed (integer).")
    )
    # Storing time as hours and minutes for easier input
    time_submitted_hours = models.IntegerField(
        null=True, blank=True, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Time: Hours")
    )
    time_submitted_minutes = models.IntegerField(
        null=True, blank=True, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(59)],
        verbose_name=_("Time: Minutes")
    )
    entry_date = models.DateField(default=timezone.now, verbose_name=_("Date of Activity"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Calculated properties (not stored in DB unless performance dictates otherwise)
    @property
    def calculated_mantras(self):
        if self.malas_submitted is not None:
            return self.malas_submitted * 108
        return 0

    @property
    def total_practice_time_in_minutes(self):
        hours = self.time_submitted_hours if self.time_submitted_hours is not None else 0
        minutes = self.time_submitted_minutes if self.time_submitted_minutes is not None else 0
        return (hours * 60) + minutes

    def clean(self):
        super().clean()
        has_malas = self.malas_submitted is not None and self.malas_submitted > 0
        has_time_hours = self.time_submitted_hours is not None and self.time_submitted_hours > 0
        has_time_minutes = self.time_submitted_minutes is not None and self.time_submitted_minutes > 0
        
        if not (has_malas or has_time_hours or has_time_minutes):
            raise ValidationError(_("Please enter a value for Malas, Time (Hours/Minutes), or both."))
        
        if self.time_submitted_hours is None:
            self.time_submitted_hours = 0
        if self.time_submitted_minutes is None:
            self.time_submitted_minutes = 0


    def save(self, *args, **kwargs):
        if self.user_activity: # Ensure user is set from the linked UserActivity
            self.user = self.user_activity.user
        # Ensure None for hours/minutes is treated as 0 if the other part of time is set
        if (self.time_submitted_hours is not None or self.time_submitted_minutes is not None):
            if self.time_submitted_hours is None:
                self.time_submitted_hours = 0
            if self.time_submitted_minutes is None:
                self.time_submitted_minutes = 0
        super().save(*args, **kwargs)

    def __str__(self):
        parts = []
        if self.malas_submitted is not None:
            parts.append(f"{self.malas_submitted} malas")
        
        total_time_min = self.total_practice_time_in_minutes
        if total_time_min > 0:
            h = total_time_min // 60
            m = total_time_min % 60
            time_str = ""
            if h > 0:
                time_str += f"{h}h"
            if m > 0:
                time_str += f" {m}m" if h > 0 else f"{m}m"
            parts.append(time_str.strip())
        
        entry_details = " and ".join(parts) if parts else "No activity logged"
        return f"{self.user.username} - {self.user_activity.get_display_name()} - {entry_details} on {self.entry_date}"

    class Meta:
        verbose_name = _("Log Entry")
        verbose_name_plural = _("Log Entries")
        ordering = ['-entry_date', '-created_at']