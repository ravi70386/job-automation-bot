from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()
driver.maximize_window()

driver.get("https://www.naukri.com")
time.sleep(5)

# Click login button
driver.find_element(By.LINK_TEXT, "Login").click()
time.sleep(3)

# Enter email
driver.find_element(By.XPATH, '//input[@placeholder="Enter your active Email ID / Username"]').send_keys("gudeseravi@gmail.com")

# Enter password
driver.find_element(By.XPATH, '//input[@placeholder="Enter your password"]').send_keys("Ravi@8688010410")

time.sleep(1)

# Click login submit
driver.find_element(By.XPATH, '//button[@type="submit"]').click()

time.sleep(10)