import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Email
from .emails import fetch_and_store_emails
from .forms import CustomSignupForm
from .ai_utils import analyze_email_light, analyze_email_full


# ==========================
# SIGNUP
# ==========================
def signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomSignupForm()

    return render(request, 'registration/signup.html', {'form': form})


# ==========================
# DELETE ALL SPAM
# ==========================
@login_required
def delete_spam(request):
    Email.objects.filter(user=request.user, is_spam=True).delete()
    return redirect('email_list')


# ==========================
# SWITCH GMAIL ACCOUNT
# ==========================
@login_required
def switch_gmail_account(request):
    token_path = f"token_{request.user.id}.json"   # ✅ per user
    if os.path.exists(token_path):
        os.remove(token_path)
    return redirect('sync_gmail')


# ==========================
# SYNC GMAIL + AUTO AI CLASSIFICATION
# ==========================
@login_required
def sync_gmail(request):
    # 🔥 Gmail fetching moved to emails.py
    fetch_and_store_emails(request.user)

    # Now classify new emails
    emails = Email.objects.filter(user=request.user, category__isnull=True)

    for email in emails:
        ai = analyze_email_light(email.subject, email.body)

        email.category = ai.get("category", "personal")
        email.summary = ai.get("summary", email.subject[:120])
        email.is_important = ai.get("important", "no") == "yes"
        email.is_spam = email.category == "spam"
        email.save()

    return redirect('email_list')


# ==========================
# SHOW EMAIL LIST
# ==========================
@login_required
def email_list(request):
    emails = Email.objects.filter(user=request.user).order_by('-received_at')
    return render(request, 'emails/email_list.html', {'emails': emails})


# ==========================
# MANUAL ANALYZE (REPLY ONLY)
# ==========================
@login_required
def process_email(request, email_id):
    email = get_object_or_404(Email, id=email_id, user=request.user)

    ai = analyze_email_full(email.subject, email.body)
    email.suggested_reply = ai.get("reply", "")

    email.save()
    return redirect('email_list')
