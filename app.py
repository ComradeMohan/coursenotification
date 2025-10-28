from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import time
import threading
import os
import traceback
import resend

app = Flask(__name__)
CORS(app)

active_sessions = {}
MAX_SESSION_DURATION = 40 * 60  # 40 minutes

# ---------------------- DRIVER SETUP ----------------------
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver

# ---------------------- EMAIL NOTIFICATION (via Resend) ----------------------
def send_email_notification(course_name, recipient_email):
    """Send email via Resend API with sender from environment variable."""
    try:
        resend_api_key = os.environ.get("RESEND_API_KEY")
        sender_email = os.environ.get("RESEND_SENDER_EMAIL")

        if not resend_api_key:
            print("[EMAIL ERROR] RESEND_API_KEY not found in environment variables")
            return False
        if not sender_email:
            print("[EMAIL ERROR] RESEND_SENDER_EMAIL not set, using default fallback sender")
            sender_email = "Comrade Mohan <comrademohan@univault.live>"

        resend.api_key = resend_api_key

        params = {
            "from": sender_email,
            "to": [recipient_email],
            "subject": f"🎉 Course {course_name} Available Now!",
            "html": f"""
                <html>
                    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
                        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                            <h2 style="color: #007bff;">🎉 Good News!</h2>
                            <p style="font-size:16px;">The course <strong>{course_name}</strong> now has available seats!</p>
                            <p>Secure your spot immediately by visiting the following portal:</p>
                            <ul>
                                <li><a href="https://univault.live/#features" target="_blank">UniVault Dashboard</a></li>
                            </ul>
                            <p style="font-size:16px;">Don’t miss out—act quickly!</p>
                            <br>
                            <p style="font-size:14px; color: gray;">
                                — <strong>Comrade Mohan</strong><br>
                                Univault Course Monitor<br>
                                <em>Helping you secure your academic success</em>
                            </p>
                        </div>
                    </body>
                </html>
            """,
        }

        email = resend.Emails.send(params)
        print(f"[EMAIL] Sent successfully to {recipient_email}: {email}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send via Resend: {e}")
        traceback.print_exc()
        return False
