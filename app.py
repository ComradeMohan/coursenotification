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
    sender_email = os.environ.get('SENDER_EMAIL', 'your-email@gmail.com')
    sender_password = os.environ.get('SENDER_PASSWORD', 'your-app-password')
    
    subject = f"Course {course_name} Found!"
    body = f"The course {course_name} has been successfully selected. Please check your enrollment."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def login(driver, username, password):
    try:
        driver.get("https://arms.sse.saveetha.com")
        time.sleep(2)

        username_field = driver.find_element(By.ID, "txtusername")
        password_field = driver.find_element(By.ID, "txtpassword")
        login_button = driver.find_element(By.ID, "btnlogin")

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False

def select_slot(driver, slot_letter):
    try:
        driver.get("https://arms.sse.saveetha.com/StudentPortal/Enrollment.aspx")
        time.sleep(2)

        slot_number = ord(slot_letter.upper()) - 64
        slot_dropdown = Select(driver.find_element(By.ID, "cphbody_ddlslot"))
        slot_dropdown.select_by_value(str(slot_number))
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Failed to select slot: {e}")
        return False

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
                    if vacancies > 0:
                        radio_button = row.find_element(By.CSS_SELECTOR, "input[type='radio']")
                        radio_button.click()
                        return {"status": "found", "vacancies": vacancies}
                    else:
                        return {"status": "full", "vacancies": 0}
        
        return {"status": "not_found"}
    except Exception as e:
        print(f"Error checking course: {e}")
        return {"status": "error", "message": str(e)}

def monitor_course(session_id, data):
    driver = setup_driver()
    
    try:
        if not login(driver, data['username'], data['password']):
            active_sessions[session_id]['status'] = 'error'
            active_sessions[session_id]['message'] = 'Login failed'
            return

        active_sessions[session_id]['status'] = 'checking'
        attempt = 0

        while active_sessions[session_id]['active']:
            attempt += 1
            active_sessions[session_id]['attempts'] = attempt
            
            if select_slot(driver, data['slot']):
                result = check_for_course(driver, data['courseCode'])
                
                active_sessions[session_id]['last_check'] = time.time()
                
                if result['status'] == 'found':
                    active_sessions[session_id]['status'] = 'found'
                    active_sessions[session_id]['message'] = f"Course found with {result['vacancies']} vacancies!"
                    
                    if data.get('email'):
                        send_email_notification(data['courseCode'], data['email'])
                    break
                elif result['status'] == 'full':
                    active_sessions[session_id]['message'] = 'Course found but no vacancies'
                else:
                    active_sessions[session_id]['message'] = 'Course not found'
            
            driver.refresh()
            time.sleep(int(data.get('checkInterval', 10)))
    
    except Exception as e:
        active_sessions[session_id]['status'] = 'error'
        active_sessions[session_id]['message'] = str(e)
    finally:
        driver.quit()

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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Course Enrollment Checker API is running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
