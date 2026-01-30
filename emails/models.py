from django.db import models
from django.contrib.auth.models import User
from django.db import models

class UserGmailToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token_json = models.JSONField(null=True, blank=True)



class Email(models.Model):
    gmail_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="emails"   
    )



    subject = models.CharField(max_length=500)
    sender = models.EmailField()
    body = models.TextField()

    category = models.CharField(max_length=50, blank=True)
    summary = models.TextField(blank=True)
    suggested_reply = models.TextField(blank=True)
    is_important = models.BooleanField(default=False)
    is_spam = models.BooleanField(default=False)

    received_at = models.DateTimeField(auto_now_add=True)
class Meta:
    unique_together = ('user', 'gmail_id')


    def __str__(self):
        return self.subject
