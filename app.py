from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import time

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

    # Call the Selenium automation function here
    result = automate_course_selection(username, password, slot, course_code)
    
    return render_template('result.html', result=result)

def automate_course_selection(username, password, slot_letter, course_code):
    # Initialize the WebDriver using WebDriver Manager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    try:
        driver.get("https://arms.sse.saveetha.com")
        time.sleep(2)  # Wait for page to load

        # Login process
        driver.find_element(By.ID, "txtusername").send_keys(username)
        driver.find_element(By.ID, "txtpassword").send_keys(password)
        driver.find_element(By.ID, "btnlogin").click()
        time.sleep(2)  # Wait for login process to complete

        # Go to enrollment page
        driver.get("https://arms.sse.saveetha.com/StudentPortal/Enrollment.aspx")
        time.sleep(2)  # Wait for enrollment page to load

        # Select slot
        slot_number = ord(slot_letter.upper()) - 64  # Convert letter to number (A=1)
        slot_dropdown = Select(driver.find_element(By.ID, "cphbody_ddlslot"))
        slot_dropdown.select_by_value(str(slot_number))  # Select by value

        time.sleep(3)  # Wait for courses to load after selecting the slot

        # Check for the specified course in the table
        rows = driver.find_elements(By.CSS_SELECTOR, "#tbltbodyslota tr")
        
        for row in rows:
            labels = row.find_elements(By.TAG_NAME, "label")
            if any(course_code in label.text for label in labels):
                radio_button = row.find_element(By.CSS_SELECTOR, "input[type='radio']")
                radio_button.click()
                return f"Course {course_code} selected successfully!"
        
        return f"Course {course_code} not found."
    
    finally:
        driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
