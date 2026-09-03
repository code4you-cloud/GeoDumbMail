from django.urls import path
#from .views import process_emails, search_emails_list, update_typo, update_in_progress
from . import views

urlpatterns = [
    path('', views.process_emails, name='process_emails'),
    path('search/', views.search_emails_list, name='search_emails_list'),
    path('update-typo/<int:email_id>/', views.update_typo, name='update_typo'),
    path('update-in-progress/', views.update_in_progress, name='update_in_progress'),
    #face and plate detected
    path('review/', views.review_queue, name='review_queue'),
    path('review/<int:pk>/', views.confirm_redaction, name='confirm_redaction'),
]
