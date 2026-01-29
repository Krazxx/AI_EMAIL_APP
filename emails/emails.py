import os
import base64
from email import message_from_bytes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .models import Email

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


# ===============================
# GET GMAIL SERVICE (PER USER)
# ===============================
def get_gmail_service(user):
    token_path = f"token_{user.id}.json"
    creds = None

    # Load existing token for THIS USER
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If token missing or invalid → login again
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES
        )

        creds = flow.run_local_server(
            port=0,
            prompt='consent',  # 🔥 Forces Google account chooser
            authorization_prompt_message='Please choose a Gmail account to connect'
        )

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


# ===============================
# FETCH & STORE EMAILS (SYNC)
# ===============================
def fetch_and_store_emails(user):
    service = get_gmail_service(user)

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
