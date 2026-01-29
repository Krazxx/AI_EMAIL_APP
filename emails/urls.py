from django.urls import path
from . import views

urlpatterns = [
    path('', views.email_list, name='email_list'),
    path('process/<int:email_id>/', views.process_email, name='process_email'),

    # 🔥 GMAIL OAUTH FLOW
    path('connect-gmail/', views.connect_gmail, name='connect_gmail'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),

    # Gmail Actions
    path('sync/', views.sync_gmail, name='sync_gmail'),
    path('switch-account/', views.switch_gmail_account, name='switch_gmail'),
    path('delete-spam/', views.delete_spam, name='delete_spam'),
]
