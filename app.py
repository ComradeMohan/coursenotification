from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from dotenv import load_dotenv
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import os

load_dotenv()
app = Flask(__name__)
CORS(app)

active_sessions = {}

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver

def send_email_notification(course_name, recipient_email):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    
    # 🆕 RENDER LOGGING
    print(f"🔵 RENDER: Sending to {recipient_email}")
    print(f"🔵 RENDER: From {sender_email}")
    print(f"🔵 RENDER: Password set? {'YES' if sender_password else 'NO'}")
    
    if not sender_email or not sender_password:
        print("❌ RENDER: ENV VARS MISSING! Check Render Dashboard!")
        return False
    
    subject = f"Course {course_name} Found!"
    body = f"The course {course_name} has been successfully selected. Please check your enrollment."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print("🔵 RENDER: Connecting SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        print("🔵 RENDER: TLS OK")
        
        print("🔵 RENDER: Logging in...")
        server.login(sender_email, sender_password)
        print("✅ RENDER: LOGIN SUCCESS!")
        
        print("🔵 RENDER: Sending...")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("✅ RENDER: EMAIL SENT SUCCESS!")
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ RENDER: WRONG APP PASSWORD! Generate new one!")
        return False
    except Exception as e:
        print(f"❌ RENDER: {str(e)}")
        return False

# ... (KEEP ALL YOUR OTHER FUNCTIONS EXACTLY SAME: login, select_slot, check_for_course, monitor_course)

@app.route('/api/start-checking', methods=['POST'])
def start_checking():
    data = request.json
    session_id = f"{data['username']}_{int(time.time())}"
    
    active_sessions[session_id] = {
        'active': True, 'status': 'starting', 'message': 'Initializing...', 
        'attempts': 0, 'last_check': None
    }
    
    thread = threading.Thread(target=monitor_course, args=(session_id, data))
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id, 'status': 'started'})

@app.route('/api/check-status/<session_id>', methods=['GET'])
def check_status(session_id):
    if session_id in active_sessions:
        return jsonify(active_sessions[session_id])
    return jsonify({'status': 'not_found'}), 404

@app.route('/api/stop-checking/<session_id>', methods=['POST'])
def stop_checking(session_id):
    if session_id in active_sessions:
        active_sessions[session_id]['active'] = False
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not_found'}), 404

# 🆕 RENDER TEST ROUTE
@app.route('/api/test-email', methods=['POST'])
def test_email():
    data = request.json
    email = data.get('email')
    print(f"🧪 RENDER TEST: {email}")
    success = send_email_notification("TEST-COURSE", email)
    return jsonify({'email_sent': success, 'message': 'Check Render logs!'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Course Enrollment Checker API is running on RENDER'})

if __name__ == '__main__':
    print("🚀 RENDER: Starting with ENV:", os.environ.get('SENDER_EMAIL'))
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
