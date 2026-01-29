import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from .models import Email

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path where Render stores your secret file
CREDENTIALS_PATH = "/etc/secrets/credentials.json"
REDIRECT_URI = "https://ai-email-app-82gm.onrender.com/oauth2callback"


# ===============================
# CREATE OAUTH FLOW
# ===============================
def get_google_flow():
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow


# ===============================
# GET GMAIL SERVICE (PER USER)
# ===============================
def get_gmail_service(user):
    token_path = f"/tmp/token_{user.id}.json"  # use temp dir on Render

    if not os.path.exists(token_path):
        return None

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build('gmail', 'v1', credentials=creds)


# ===============================
# START GMAIL LOGIN
# ===============================
def start_gmail_auth(request):
    flow = get_google_flow()

    auth_url, _ = flow.authorization_url(
        prompt='consent',
        access_type='offline'
    )

    return auth_url


# ===============================
# HANDLE GOOGLE CALLBACK
# ===============================
def save_user_token(request, user):
    flow = get_google_flow()
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials
    token_path = f"/tmp/token_{user.id}.json"

    with open(token_path, 'w') as token:
        token.write(creds.to_json())


# ===============================
# FETCH & STORE EMAILS (SYNC)
# ===============================
def fetch_and_store_emails(user):
    service = get_gmail_service(user)
    if not service:
        return

    results = service.users().messages().list(
        userId='me',
        maxResults=10
    ).execute()

    messages = results.get('messages', [])

    for msg in messages:
        msg_id = msg['id']

        if Email.objects.filter(gmail_id=msg_id, user=user).exists():
            continue

        message = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        payload = message['payload']
        headers = payload.get("headers", [])

        subject = ""
        sender = ""

        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            if header['name'] == 'From':
                sender = header['value']

        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode(errors="ignore")
                        break

        Email.objects.create(
            user=user,
            gmail_id=msg_id,
            sender=sender,
            subject=subject,
            body=body
        )

    print("Emails synced successfully!")
