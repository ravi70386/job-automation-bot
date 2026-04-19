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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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

    # Round Robin selection logic
    POINTER_FILE = ".resume_pointer"
    current_index = 0
    if os.path.exists(POINTER_FILE):
        try:
            with open(POINTER_FILE, "r") as f:
                current_index = int(f.read().strip())
        except:
            current_index = 0
    
    next_index = current_index % len(files)
    resume_file = files[next_index]
    RESUME_PATH = os.path.join(local_resumes, resume_file)

    with open(POINTER_FILE, "w") as f:
        f.write(str(next_index + 1))

    logger.info(f"Round Robin Selection: [{next_index + 1}/{len(files)}] {resume_file}")

    # Set Chrome Options for Premium Headless Execution
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Create lock file FIRST
    LOCK_FILE = ".bot_locked"
    with open(LOCK_FILE, "w") as f: f.write(str(os.getpid()))

    logger.info("Setting up Chrome Driver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_window_size(1920, 1080)
        wait = WebDriverWait(driver, 30)
    except Exception as e:
        logger.error(f"CHROME DRIVER ERROR: {str(e)}")
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
        return

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
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
        logger.info("Browser closed.")

if __name__ == "__main__":
    run_update()