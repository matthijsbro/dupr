# accounts/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _

# Import Wagtail's base user forms
from wagtail.users.forms import UserCreationForm, UserEditForm

# Import your Category model from the teachings app
from teachings.models import Category

class CustomUserEditForm(UserEditForm):
    """
    Custom form for editing users in the Wagtail admin.
    This form includes the custom 'categories' field.
    """
    # Define the categories field
    # ModelMultipleChoiceField is used for ManyToMany relationships
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all().order_by('name'), # Get all available Category snippets
        required=False, # Make it optional to assign categories
        widget=forms.CheckboxSelectMultiple, # Use checkboxes for a user-friendly interface
        label=_("Access Categories"),
        help_text=_("Content categories this user should have access to.")
    )

    # The base UserEditForm's Meta class needs to be inherited
    class Meta(UserEditForm.Meta):
        # Add 'categories' to the list of fields displayed in the form
        # Convert the original tuple to a list to allow appending
        fields = list(UserEditForm.Meta.fields) + ['categories']


class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for creating new users in the Wagtail admin.
    This form also includes the custom 'categories' field.
    """
    # Define the categories field exactly as in the edit form
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Access Categories"),
        help_text=_("Content categories this user should have access to.")
    )

    # Inherit the Meta class from the base UserCreationForm
    class Meta(UserCreationForm.Meta):
        # Add 'categories' to the list of fields
        fields = list(UserCreationForm.Meta.fields) + ['categories']

    # Optional: Override save method if needed for M2M handling on creation
    # Usually, ModelForm handles this correctly, but uncomment and adapt if necessary.
    # def save(self, commit=True):
    #     user = super().save(commit=False)
    #     # Custom processing before saving the user instance, if needed
    #     if commit:
    #         user.save()
    #         # Important: Ensure ManyToMany data is saved after the user instance
    #         self.save_m2m()
    #     return user