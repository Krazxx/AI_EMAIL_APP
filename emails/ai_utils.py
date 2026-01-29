import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
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
