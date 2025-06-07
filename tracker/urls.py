# tracker/urls.py
from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('log/add/', views.LogEntryCreateView.as_view(), name='logentry-add'),
    path('log/<int:pk>/edit/', views.LogEntryUpdateView.as_view(), name='logentry-edit'),
    path('log/<int:pk>/delete/', views.LogEntryDeleteView.as_view(), name='logentry-delete'),
    path('history/', views.LogEntryHistoryView.as_view(), name='logentry-history'),
    path('practice/add/', views.UserActivityAddPracticeView.as_view(), name='practice-add'),
    path('practice/<int:pk>/stop/', views.UserActivityStopTrackingView.as_view(), name='practice-stop'),
]