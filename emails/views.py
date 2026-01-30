import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Email
from .ai_utils import fetch_and_store_emails
from django.db.models import Q
from .forms import CustomSignupForm
from .ai_utils import analyze_email_light, analyze_email_full
from django.shortcuts import redirect
from .ai_utils import start_gmail_auth
from django.shortcuts import redirect
from .ai_utils import save_user_token

def oauth2callback(request):
    save_user_token(request, request.user)
    return redirect('/emails/')


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
    token_path = f"token_{request.user.id}.json"   # ✅ per user
    if os.path.exists(token_path):
        os.remove(token_path)
    return redirect('sync_gmail')


# ==========================
# SYNC GMAIL + AUTO AI CLASSIFICATION
# ==========================
@login_required
def sync_gmail(request):
    # Step 1: Fetch from Gmail
    fetch_and_store_emails(request.user)

    # Step 2: Get emails that need AI classification
    emails = Email.objects.filter(user=request.user).filter(
        Q(category__isnull=True) | Q(category="unknown")
    )

    # Step 3: Run AI
    for email in emails:
        print("🤖 Classifying:", email.subject)

        ai = analyze_email_light(email.subject, email.body)

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
# MANUAL ANALYZE (REPLY ONLY)
# ==========================
@login_required
def process_email(request, email_id):
    email = get_object_or_404(Email, id=email_id, user=request.user)

    ai = analyze_email_full(email.subject, email.body)
    email.suggested_reply = ai.get("reply", "")

    email.save()
    return redirect('email_list')




