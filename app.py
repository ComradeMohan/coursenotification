from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import io

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']
    slot = request.form['slot']
    course_code = request.form['course_code']

    # Run the Selenium automation and capture logs
    log_output = io.StringIO()
    result = automate_course_selection(username, password, slot, course_code, log_output)
    logs = log_output.getvalue()
    
    return render_template('result.html', result=result, logs=logs)

def automate_course_selection(username, password, slot_letter, course_code, log_output):
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize the WebDriver using WebDriver Manager with options
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    log_output.write("Starting Selenium Automation...\n")

    try:
        driver.get("https://arms.sse.saveetha.com")
        log_output.write("Navigated to login page.\n")
        time.sleep(2)

        # Login process
        driver.find_element(By.ID, "txtusername").send_keys(username)
        driver.find_element(By.ID, "txtpassword").send_keys(password)
        driver.find_element(By.ID, "btnlogin").click()
        log_output.write("Logged in successfully.\n")
        time.sleep(2)

        # Navigate to enrollment page
        driver.get("https://arms.sse.saveetha.com/StudentPortal/Enrollment.aspx")
        log_output.write("Navigated to enrollment page.\n")
        time.sleep(2)

        # Select slot
        slot_number = ord(slot_letter.upper()) - 64
        slot_dropdown = Select(driver.find_element(By.ID, "cphbody_ddlslot"))
        slot_dropdown.select_by_value(str(slot_number))
        log_output.write(f"Selected slot {slot_letter}.\n")
        time.sleep(3)

        # Check for the specified course in the table
        rows = driver.find_elements(By.CSS_SELECTOR, "#tbltbodyslota tr")
        for row in rows:
            labels = row.find_elements(By.TAG_NAME, "label")
            if any(course_code in label.text for label in labels):
                radio_button = row.find_element(By.CSS_SELECTOR, "input[type='radio']")
                radio_button.click()
                log_output.write(f"Course {course_code} selected successfully!\n")
                return f"Course {course_code} selected successfully!"
        
        log_output.write(f"Course {course_code} not found.\n")
        return f"Course {course_code} not found."
    finally:
        driver.quit()
        log_output.write("Selenium Automation Completed.\n")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
