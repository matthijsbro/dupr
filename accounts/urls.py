# accounts/urls.py (Example)
from django.urls import path, include

urlpatterns = [
    # Include default auth urls (login, logout, password reset, etc.)
    path('', include('django.contrib.auth.urls')),
    # Add other account-related urls here later (e.g., profile, dashboard)
]