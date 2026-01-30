import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.utils import timezone
from .models import Email, UserGmailToken
from .models import UserGmailToken, Email
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from django.utils import timezone


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
        print("❌ No Gmail token in database")
        return

    creds = Credentials.from_authorized_user_info(token_obj.token_json, SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    try:
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=15
        ).execute()

        messages = results.get('messages', [])
        print("📨 Gmail messages found:", messages)

        if not messages:
            print("📭 Inbox empty")
            return

        for msg in messages:
            msg_id = msg['id']

            # Skip if already saved
            if Email.objects.filter(gmail_id=msg_id, user=user).exists():
                continue

            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")

            # Extract body
            body = ""
            payload = message['payload']

            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8', errors='ignore')
                        break
            elif 'data' in payload['body']:
                body = base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8', errors='ignore')

            Email.objects.create(
                user=user,
                gmail_id=msg_id,
                subject=subject,
                sender=sender,
                body=body,
                received_at=timezone.now()
            )

        print("✅ Emails stored successfully")

    except Exception as e:
        print("❌ Gmail Fetch Error:", e)
