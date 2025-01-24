from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import io
import traceback
from webdriver_manager.chrome import ChromeDriverManager

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

    log_output = io.StringIO()

    try:
        result = automate_course_selection(username, password, slot, course_code, log_output)
        logs = log_output.getvalue()
        return render_template('result.html', result=result, logs=logs)
    except Exception as e:
        logs = log_output.getvalue()
        logs += "\n" + traceback.format_exc()
        return render_template('result.html', result=f"An error occurred: {str(e)}", logs=logs)

def automate_course_selection(username, password, slot_letter, course_code, log_output):
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        log_output.write("Starting automation...\n")
        driver.get("https://arms.sse.saveetha.com")
        log_output.write("Navigated to the login page.\n")

        # Perform login
        driver.find_element(By.ID, "txtusername").send_keys(username)
        driver.find_element(By.ID, "txtpassword").send_keys(password)
        driver.find_element(By.ID, "btnlogin").click()
        log_output.write("Logged in successfully.\n")

        # Go to the enrollment page
        driver.get("https://arms.sse.saveetha.com/StudentPortal/Enrollment.aspx")
        log_output.write("Opened the enrollment page.\n")

        # Select slot
        slot_number = ord(slot_letter.upper()) - 64  # Convert letter to number (A=1)
        slot_dropdown = Select(driver.find_element(By.ID, "cphbody_ddlslot"))
        slot_dropdown.select_by_value(str(slot_number))
        log_output.write(f"Selected slot: {slot_letter}\n")

        # Wait for the table to load
        driver.implicitly_wait(5)

        # Check for the course code
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
        log_output.write("Browser session ended.\n")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
