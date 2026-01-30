import requests
import json
import re
import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .models import Email
from django.utils import timezone

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']



def start_gmail_auth(request):
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri="https://ai-email-app-82gm.onrender.com/emails/oauth2callback/"

    )

    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )

    request.session['state'] = state
    return auth_url



from .models import UserGmailToken
import json

def save_user_token(request, user):
    state = request.session['state']

    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        state=state,
        redirect_uri="https://ai-email-app-82gm.onrender.com/emails/oauth2callback/"

    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials

    obj, created = UserGmailToken.objects.get_or_create(user=user)
    obj.token_json = json.loads(creds.to_json())
    obj.save()




OLLAMA_URL = "https://vanquishable-liplike-rosina.ngrok-free.dev/api/generate"
MODEL = "llama3"



# =========================================
# LIGHT AI — used during SYNC (FAST)
# Only category + summary + importance
# =========================================
def analyze_email_light(subject, body):
    prompt = f"""
You are an AI email classifier.

Return ONLY JSON.

{{
  "category": "work/personal/spam/urgent/security/promo",
  "summary": "short summary",
  "important": "yes/no"
}}

EMAIL SUBJECT: {subject}
EMAIL BODY: {body}
"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }).json()["response"]

        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group(0))

    except Exception as e:
        print("LIGHT AI ERROR:", e)

    return {"category": "unknown", "summary": "", "important": "no"}


# =========================================
# FULL AI — used when clicking ANALYZE
# Generates reply
# =========================================
def analyze_email_full(subject, body):
    prompt = f"""
You are an AI email assistant.

Return ONLY JSON.

{{
  "reply": "short helpful reply"
}}

EMAIL SUBJECT: {subject}
EMAIL BODY: {body}
"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }).json()["response"]

        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group(0))

    except Exception as e:
        print("FULL AI ERROR:", e)

    return {"reply": ""}


def fetch_and_store_emails(user):
    token_path = f"token_{user.id}.json"

    if not os.path.exists(token_path):
        print("❌ No Gmail token found")
        return

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    try:
        # Fetch latest 15 emails
        results = service.users().messages().list(userId='me', maxResults=15).execute()
        messages = results.get('messages', [])

        if not messages:
            print("📭 No emails found")
            return

        for msg in messages:
            msg_id = msg['id']

            # Skip if already saved
            if Email.objects.filter(gmail_id=msg_id, user=user).exists():
                continue

            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            headers = message['payload']['headers']

            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")

            # Extract body
            body = ""
            parts = message['payload'].get('parts', [])

            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
            else:
                data = message['payload']['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # Save to DB
            Email.objects.create(
                user=user,
                gmail_id=msg_id,
                subject=subject,
                sender=sender,
                body=body,
                received_at=timezone.now()
            )

        print("✅ Emails fetched successfully")

    except Exception as e:
        print("❌ Gmail Fetch Error:", e)