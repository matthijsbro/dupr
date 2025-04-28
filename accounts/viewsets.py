# accounts/viewsets.py

from wagtail.users.views.users import UserViewSet as WagtailUserViewSet
from .forms import CustomUserCreationForm, CustomUserEditForm

class CustomUserViewSet(WagtailUserViewSet):
    """
    Override Wagtail's UserViewSet to plug in the custom user forms.
    """
    def get_form_class(self, for_update=False):
        # for_update=True → edit form; otherwise → creation form
        if for_update:
            return CustomUserEditForm
        return CustomUserCreationForm