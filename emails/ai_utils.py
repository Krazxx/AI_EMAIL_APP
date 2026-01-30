import requests
import json
import re
import os
import base64
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.utils import timezone
from .models import Email, UserGmailToken

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


# ================= GOOGLE OAUTH =================
def start_gmail_auth(request):
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri="https://ai-email-app-82gm.onrender.com/emails/oauth2callback/"
    )
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    request.session['state'] = state
    return auth_url


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

    obj, _ = UserGmailToken.objects.get_or_create(user=user)
    obj.token_json = json.loads(creds.to_json())
    obj.save()


# ================= AI CONFIG =================
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    print("❌ OPENROUTER_API_KEY not set")


def ask_ai(prompt):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )

        print("🧠 AI STATUS:", r.status_code)
        print("🧠 AI RAW:", r.text[:300])

        if r.status_code != 200:
            return None

        data = r.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI ERROR:", e)
        return None


# ================= LIGHT AI =================
def analyze_email_light(subject, body):
    prompt = f"""
You are an email classifier.

STRICT RULES:
- Output ONLY valid JSON
- No explanations
- No markdown

FORMAT:
{{
  "category": "work/personal/spam/urgent/security/promo",
  "summary": "short summary",
  "important": "yes/no"
}}

SUBJECT: {subject}
BODY: {body}
"""

   
   
   
   
   
   
   
   
    raw = ask_ai(prompt)
    if not raw:
        return {"category": "unknown", "summary": "", "important": "no"}

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
       try:
        return json.loads(match.group(0))
       except:
        print("⚠️ JSON parse error (light)")

    return {"category": "unknown", "summary": "", "important": "no"}


# ================= FULL AI (REPLY) =================
def analyze_email_full(subject, body):
    prompt = f"""
You are an AI email assistant.

STRICT RULES:
- Output ONLY valid JSON
- No explanations
- No markdown

FORMAT:
{{ "reply": "short helpful reply" }}

SUBJECT: {subject}
BODY: {body}
"""

    raw = ask_ai(prompt)
    if not raw:
        return {"reply": "AI server not responding."}

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
         return json.loads(match.group(0))
        except:
         print("⚠️ JSON parse error (full)")

    return {"reply": "AI response format error."}


# ================= GMAIL FETCH =================
def fetch_and_store_emails(user):
    try:
        token_obj = UserGmailToken.objects.get(user=user)
    except UserGmailToken.DoesNotExist:
        print("❌ No Gmail token in database")
        return

    creds = Credentials.from_authorized_user_info(
        token_obj.token_json,
        SCOPES
    )

    service = build('gmail', 'v1', credentials=creds)


    try:
        results = service.users().messages().list(userId='me', maxResults=15).execute()
        messages = results.get('messages', [])

        if not messages:
            print("📭 No emails found")
            return

        for msg in messages:
            msg_id = msg['id']

            if Email.objects.filter(gmail_id=msg_id, user=user).exists():
                continue

            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = message['payload']['headers']

            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")

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
