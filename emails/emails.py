import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.utils import timezone
from .models import Email, UserGmailToken

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

CREDENTIALS_PATH = "/etc/secrets/credentials.json"
REDIRECT_URI = "https://ai-email-app-82gm.onrender.com/emails/oauth2callback/"


# ===============================
# CREATE OAUTH FLOW
# ===============================
def get_google_flow():
    return Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


# ===============================
# START GMAIL LOGIN
# ===============================
def start_gmail_auth(request):
    flow = get_google_flow()
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return auth_url


# ===============================
# SAVE TOKEN TO DATABASE
# ===============================
def save_user_token(request, user):
    flow = get_google_flow()
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials

    obj, _ = UserGmailToken.objects.get_or_create(user=user)
    obj.token_json = json.loads(creds.to_json())
    obj.save()


# ===============================
# FETCH EMAILS FROM GMAIL
# ===============================
def fetch_and_store_emails(user):
    try:
        token_obj = UserGmailToken.objects.get(user=user)
    except UserGmailToken.DoesNotExist:
        print("❌ No Gmail token found in DB")
        return

    creds = Credentials.from_authorized_user_info(token_obj.token_json, SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

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

        Email.objects.create(
            user=user,
            gmail_id=msg_id,
            subject=subject,
            sender=sender,
            body=body,
            received_at=timezone.now()
        )

    print("✅ Gmail sync completed")
