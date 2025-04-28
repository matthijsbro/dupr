
from wagtail.users.apps import WagtailUsersAppConfig

class AccountsAppConfig(WagtailUsersAppConfig):
    # dotted path to the viewset you just made
    user_viewset = 'accounts.viewsets.CustomUserViewSet'
    default_auto_field = 'django.db.models.BigAutoField'
