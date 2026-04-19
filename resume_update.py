import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ===============================
# LOGGING SETUP
# ===============================
os.makedirs("logs", exist_ok=True)
log_file = os.path.join("logs", f"bot_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_update():
    load_dotenv()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")

    if not EMAIL or not PASSWORD:
        logger.error("EMAIL or PASSWORD not found in environment variables.")
        return

    # Check local "resumes" folder
    local_resumes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resumes")
    os.makedirs(local_resumes, exist_ok=True)
    
    files = sorted([f for f in os.listdir(local_resumes) if f.lower().endswith(".pdf")])

    if len(files) == 0:
        logger.error("No resumes found in folder.")
        return

    day = datetime.now().day
    resume_file = files[(day - 1) % len(files)]
    RESUME_PATH = os.path.join(local_resumes, resume_file)

    logger.info(f"Today's resume: {resume_file}")

    # Set Chrome Options for Headless Mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set a common user agent to avoid detection
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    wait = WebDriverWait(driver, 30)

    try:
        logger.info("Opening Naukri...")
        driver.get("https://www.naukri.com")
        time.sleep(3)

        logger.info("Clicking Login...")
        wait.until(EC.element_to_be_clickable((By.XPATH, '//a[text()="Login"]'))).click()

        logger.info("Entering credentials...")
        wait.until(EC.visibility_of_element_located((By.XPATH, '//input[contains(@placeholder,"Email")]'))).send_keys(EMAIL)
        wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@type="password"]'))).send_keys(PASSWORD)
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()

        logger.info("Logged in successfully. Waiting for redirect...")
        time.sleep(8)

        logger.info("Navigating to profile page...")
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(5)

        logger.info("Finding Update Resume button...")
        btn = wait.until(EC.presence_of_element_located((By.XPATH, '//input[contains(@value,"Update")]')))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(2)

        try:
            btn.click()
        except:
            driver.execute_script("arguments[0].click();", btn)

        logger.info("Update Resume button clicked. Uploading file...")
        time.sleep(3)

        file_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="file"]')))
        file_input.send_keys(RESUME_PATH)

        logger.info(f"Uploaded Successfully: {resume_file}")
        time.sleep(10)

    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
    finally:
        driver.quit()
        logger.info("Browser closed.")

if __name__ == "__main__":
    run_update()