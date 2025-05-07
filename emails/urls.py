from django.urls import path
from .views import process_emails, search_emails_list, update_typo, update_in_progress

urlpatterns = [
    path('', process_emails, name='process_emails'),
    path('search/', search_emails_list, name='search_emails_list'),
    path('update-typo/<int:email_id>/', update_typo, name='update_typo'),
    path('update-in-progress/', update_in_progress, name='update_in_progress'),
]
