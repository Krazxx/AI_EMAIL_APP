import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Email
from .forms import CustomSignupForm
from .models import UserGmailToken
from .ai_utils import (
    fetch_and_store_emails,
    analyze_email_light,
    analyze_email_full,
    start_gmail_auth,
    save_user_token
)

# ==========================
# GMAIL OAUTH CALLBACK
# ==========================
def oauth2callback(request):
    save_user_token(request, request.user)
    return redirect('email_list')


def connect_gmail(request):
    auth_url = start_gmail_auth(request)
    return redirect(auth_url)


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
    # Delete stored Gmail token from DB
    UserGmailToken.objects.filter(user=request.user).delete()

    print("🔄 Gmail token deleted. Need re-authentication.")

    # Redirect user to Gmail connect flow
    return redirect('connect_gmail')


# ==========================
# 🔥 SYNC GMAIL + AUTO AI CLASSIFICATION
# ==========================
@login_required
def sync_gmail(request):
    # Step 1: Fetch new emails
    fetch_and_store_emails(request.user)

    # Step 2: Get emails that still need AI processing
    emails = Email.objects.filter(user=request.user).filter(
        Q(category__isnull=True) |
        Q(category="") |
        Q(category="unknown") |
        Q(summary__isnull=True) |
        Q(summary="")
    )

    print(f"📬 Emails needing AI classification: {emails.count()}")

    # Step 3: Run AI classifier
    for email in emails:
        print("🤖 Classifying:", email.subject)

        ai = analyze_email_light(email.subject, email.body)
        print("🧠 AI RESULT:", ai)

        email.category = ai.get("category", "personal").lower()
        email.summary = ai.get("summary", email.subject[:120])
        email.is_important = ai.get("important", "no").lower() == "yes"
        email.is_spam = email.category == "spam"

        email.save()

    print("✅ AI classification complete")
    return redirect('email_list')


# ==========================
# SHOW EMAIL LIST
# ==========================
@login_required
def email_list(request):
    emails = Email.objects.filter(user=request.user).order_by('-received_at')
    return render(request, 'emails/email_list.html', {'emails': emails})


# ==========================
# MANUAL ANALYZE (REPLY)
# ==========================
@login_required
def process_email(request, email_id):
    email = get_object_or_404(Email, id=email_id, user=request.user)

    ai = analyze_email_full(email.subject, email.body)
    print("🤖 Reply AI result:", ai)

    email.suggested_reply = ai.get("reply", "AI could not generate reply.")
    email.save()

    return redirect('email_list')
