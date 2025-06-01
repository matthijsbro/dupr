# tracker/urls.py

from django.urls import path
from . import views  # Import views from the current app directory

app_name = 'tracker'  # Define an application namespace for easier URL reversing

urlpatterns = [
    # Dashboard View (e.g., /tracker/)
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Log Entry Views
    path('log/add/', views.LogEntryCreateView.as_view(), name='logentry-add'),
    path('log/<int:pk>/edit/', views.LogEntryUpdateView.as_view(), name='logentry-edit'),
    path('log/<int:pk>/delete/', views.LogEntryDeleteView.as_view(), name='logentry-delete'),
    path('history/', views.LogEntryHistoryView.as_view(), name='logentry-history'),

    # User Activity Views (for users adding activities they track)
    path('activities/add_predefined/', views.UserActivityAddPredefinedView.as_view(), name='useractivity-add-predefined'),

    # Future paths for listing/managing UserActivity could go here, e.g.:
    # path('activities/', views.UserActivityListView.as_view(), name='useractivity-list'),
    # path('activities/<int:pk>/archive/', views.UserActivityArchiveView.as_view(), name='useractivity-archive'),
]