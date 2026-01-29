from django.urls import path
from .views import email_list, process_email, sync_gmail
from emails import views

urlpatterns = [
    path('', email_list, name='email_list'),
    path('process/<int:email_id>/', process_email, name='process_email'),
    path('sync/', sync_gmail, name='sync_gmail'),
    path('sync/', views.sync_gmail, name='sync_gmail'),
    path('switch-account/', views.switch_gmail_account, name='switch_gmail'),
    path('delete-spam/', views.delete_spam, name='delete_spam'),



]
