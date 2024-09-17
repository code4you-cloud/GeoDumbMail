from django.urls import path
from .views import process_emails, search_emails_list

urlpatterns = [
    path('', process_emails, name='process_emails'),
    path('search/', search_emails_list, name='search_emails_list'),
]

