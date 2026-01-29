from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class CustomSignupForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Username'
    }), help_text='')

    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password'
    }), help_text='')

    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password'
    }), help_text='')

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')
