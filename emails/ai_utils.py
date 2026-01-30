import requests
import json
import re
import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


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

    token_path = f"token_{user.id}.json"
    with open(token_path, 'w') as token:
        token.write(creds.to_json())


OLLAMA_URL = " https://vanquishable-liplike-rosina.ngrok-free.dev"
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
