from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

options = Options()
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.517 Safari/537.36'
options.add_argument('user-agent={0}'.format(user_agent))

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 40)
action = ActionChains(driver)

driver.get("https://www.crexi.com/properties/1988864/pennsylvania-greenfield-of-perkiomen-valley")

# Wait for the address h2 to be present
address_elem = wait.until(
    EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'address-line')]//h2"))
)

# Move to element (optional, like your Phoenix code) and print text
action.move_to_element(address_elem).perform()
print("Property Address:", address_elem.text)

driver.quit()
