from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from datetime import datetime
import os
import time

# ===============================
# LOAD .env FILE
# ===============================
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# ===============================
# RESUME FOLDER
# Keep 4 resumes here
# ===============================
# Check local "resumes" folder first
local_resumes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resumes")
# Fallback to Windows path if needed
windows_resumes = r"C:\Users\G RAVI KUMAR\Desktop\resumes"

resume_folder = local_resumes if os.path.exists(local_resumes) else windows_resumes

try:
    # Get all PDF resumes
    files = sorted(
        [f for f in os.listdir(resume_folder) if f.lower().endswith(".pdf")]
    )
except FileNotFoundError:
    print(f"No resumes folder found. Please ensure {local_resumes} or {windows_resumes} exists.")
    exit()

# Check resumes exist
if len(files) == 0:
    print("No resumes found in folder.")
    exit()

# ===============================
# DAILY AUTO ROTATION
# Day1 file1
# Day2 file2
# Day3 file3
# Day4 file4
# Day5 file1 repeat
# ===============================
day = datetime.now().day
resume_file = files[(day - 1) % len(files)]

RESUME_PATH = os.path.join(resume_folder, resume_file)

print("Today Uploading:", resume_file)

# ===============================
# OPEN CHROME
# ===============================
driver = webdriver.Chrome()
driver.maximize_window()
wait = WebDriverWait(driver, 30)

try:
    # Open Naukri
    driver.get("https://www.naukri.com")
    time.sleep(3)

    # Click Login
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//a[text()="Login"]')
        )
    ).click()

    # Enter Email
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, '//input[contains(@placeholder,"Email")]')
        )
    ).send_keys(EMAIL)

    # Enter Password
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, '//input[@type="password"]')
        )
    ).send_keys(PASSWORD)

    # Submit Login
    driver.find_element(
        By.XPATH,
        '//button[@type="submit"]'
    ).click()

    print("Logged in successfully")
    time.sleep(8)

    # Open Profile Page
    driver.get("https://www.naukri.com/mnjuser/profile")
    time.sleep(5)

    # Find Update Resume Button
    btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//input[contains(@value,"Update")]')
        )
    )

    # Scroll to button
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        btn
    )
    time.sleep(2)

    # Click Button
    try:
        btn.click()
    except:
        driver.execute_script(
            "arguments[0].click();",
            btn
        )

    print("Update Resume button clicked")
    time.sleep(3)

    # Upload Resume
    file_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//input[@type="file"]')
        )
    )

    file_input.send_keys(RESUME_PATH)

    print("Uploaded Successfully:", resume_file)

    time.sleep(10)

except Exception as e:
    print("ERROR:", e)
    input("Press Enter to close...")

finally:
    driver.quit()