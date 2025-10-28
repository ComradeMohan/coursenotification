from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
def send_email_notification(course_name, recipient_email):
    """
    Send email via Resend.
    Currently always sends to k.nobitha666@gmail.com for testing.
    """
    try:
        resend_api_key = os.environ.get("RESEND_API_KEY")
        if not resend_api_key:
            print("[EMAIL ERROR] RESEND_API_KEY not found in environment variables")
            return False

        resend.api_key = resend_api_key
        sender_email = os.getenv("SENDER_EMAIL")
        print(f"[ENV] Sender email from environment: {sender_email}")

        # Always send to your Resend test email for now
        test_email = "k.nobitha666@gmail.com"

        params = {
            "from":str(sender_email),
            "to": [recipient_email],
            "subject": f"🎉 Course {course_name} Available Now!",
"html": f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h2 style="color: #007bff;">🎉 Good News!</h2>
                <p style="font-size:16px;">The course <strong>{course_name}</strong> now has available seats!</p>
                <p>Secure your spot immediately by visiting the following portals:</p>
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
"""
,
        }

        email = resend.Emails.send(params)
        print(f"[EMAIL] Sent successfully to {test_email}: {email}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send via Resend: {e}")
        traceback.print_exc()
        return False

# ---------------------- PORTAL LOGIN ----------------------
def login(driver, username, password):
    try:
        driver.get("https://arms.sse.saveetha.com")
        time.sleep(2)
        driver.find_element(By.ID, "txtusername").send_keys(username)
        driver.find_element(By.ID, "txtpassword").send_keys(password)
        driver.find_element(By.ID, "btnlogin").click()
        time.sleep(2)

        if "Invalid username or password" in driver.page_source:
            print(f"[LOGIN] Invalid credentials for {username}")
            return False

        if "StudentPortal" in driver.current_url:
            print(f"[LOGIN] Successful for {username}")
            return True

        print(f"[LOGIN] Unknown login state")
        return False
    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        traceback.print_exc()
        return False

# ---------------------- SLOT SELECTION ----------------------
def select_slot(driver, slot_letter):
    try:
        driver.get("https://arms.sse.saveetha.com/StudentPortal/Enrollment.aspx")
        time.sleep(2)
        slot_number = ord(slot_letter.upper()) - 64
        slot_dropdown = Select(driver.find_element(By.ID, "cphbody_ddlslot"))
        slot_dropdown.select_by_value(str(slot_number))
        time.sleep(2)
        print(f"[SLOT] Slot {slot_letter} selected")
        return True
    except Exception as e:
        print(f"[SLOT ERROR] {e}")
        traceback.print_exc()
        return False

# ---------------------- COURSE CHECK ----------------------
def check_for_course(driver, course_code):
    try:
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, "#tbltbodyslota tr")

        for row in rows:
            labels = row.find_elements(By.TAG_NAME, "label")
            badges = row.find_elements(By.CLASS_NAME, "badge")

            for label, badge in zip(labels, badges):
                if course_code in label.text:
                    vacancies = int(badge.text)
                    print(f"[CHECK] Found {course_code} with {vacancies} vacancies")
                    if vacancies > 0:
                        radio_button = row.find_element(By.CSS_SELECTOR, "input[type='radio']")
                        radio_button.click()
                        return {"status": "found", "vacancies": vacancies}
                    else:
                        return {"status": "full", "vacancies": 0}

        return {"status": "not_found"}
    except Exception as e:
        print(f"[COURSE CHECK ERROR] {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# ---------------------- COURSE MONITOR ----------------------
def monitor_course(session_id, data):
    driver = setup_driver()
    start_time = time.time()

    try:
        username = data['username']
        password = data['password']
        email = data.get('email')
        course_code = data['courseCode']
        slot = data['slot']
        check_interval = int(data.get('checkInterval', 10))

        print(f"[SESSION START] {session_id} - Monitoring {course_code} every {check_interval}s")

        if not login(driver, username, password):
            active_sessions[session_id]['status'] = 'error'
            active_sessions[session_id]['message'] = 'Invalid credentials'
            print(f"[SESSION ERROR] Invalid credentials for {username}")
            return

        active_sessions[session_id]['status'] = 'checking'
        attempt = 0

        while active_sessions[session_id]['active']:
            attempt += 1
            elapsed = time.time() - start_time
            active_sessions[session_id]['attempts'] = attempt
            active_sessions[session_id]['last_check'] = time.strftime("%H:%M:%S")

            if elapsed > MAX_SESSION_DURATION:
                active_sessions[session_id]['active'] = False
                active_sessions[session_id]['status'] = 'timeout'
                active_sessions[session_id]['message'] = 'Session expired after 40 minutes'
                print(f"[SESSION TIMEOUT] {session_id} expired after {elapsed:.2f} seconds")
                break

            if select_slot(driver, slot):
                result = check_for_course(driver, course_code)

                if result['status'] == 'found':
                    msg = f"Course found with {result['vacancies']} vacancies!"
                    print(f"[SUCCESS] {msg}")
                    active_sessions[session_id]['status'] = 'found'
                    active_sessions[session_id]['message'] = msg
                    
                    if email:
                        print(f"[EMAIL] Sending notification to {email}")
                        if send_email_notification(course_code, email):
                            active_sessions[session_id]['message'] += " (Email sent)"
                        else:
                            active_sessions[session_id]['message'] += " (Email failed)"
                            print("[WARN] Email sending failed")
                    break
                elif result['status'] == 'full':
                    active_sessions[session_id]['message'] = 'Course found but no vacancies'
                else:
                    active_sessions[session_id]['message'] = 'Course not found'

            time.sleep(check_interval)

    except Exception as e:
        print(f"[SESSION ERROR] {e}")
        traceback.print_exc()
        active_sessions[session_id]['status'] = 'error'
        active_sessions[session_id]['message'] = str(e)
    finally:
        driver.quit()
        print(f"[SESSION END] {session_id} closed")

# ---------------------- API ROUTES ----------------------
@app.route('/api/start-checking', methods=['POST'])
def start_checking():
    data = request.json
    session_id = f"{data['username']}_{int(time.time())}"

    active_sessions[session_id] = {
        'active': True,
        'status': 'starting',
        'message': 'Initializing...',
        'attempts': 0,
        'last_check': None
    }

    thread = threading.Thread(target=monitor_course, args=(session_id, data))
    thread.daemon = True
    thread.start()

    print(f"[NEW SESSION] {session_id} started")
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
        print(f"[SESSION STOPPED] {session_id}")
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not_found'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Course Enrollment Checker API is running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)





