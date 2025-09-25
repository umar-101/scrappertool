from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from utils.cleaners import clean_price, clean_size, clean_date, clean_brokers
import time

BASE_URL = "https://www.crexi.com/properties/Auctions?pageSize=60"

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_crexi():
    driver = get_driver()
    driver.get(BASE_URL)
    time.sleep(3)
    results = []

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")

        for link in soup.select("a.cui-card-cover-link"):
            url = link.get("href")
            if not url.startswith("http"):
                url = "https://www.crexi.com" + url

            driver.get(url)
            time.sleep(2)
            prop_soup = BeautifulSoup(driver.page_source, "html.parser")

            record = {
                "site": "CREXI",
                "url": url,
                "property_name": prop_soup.select_one("h1").text.strip() if prop_soup.select_one("h1") else None,
                "address": prop_soup.select_one("div.property-info-container.addresses h2.text").text.strip() if prop_soup.select_one("div.property-info-container.addresses h2.text") else None,
                "property_type": prop_soup.select_one("span.detail-name:contains('Property Type') ~ span.detail-value").text.strip() if prop_soup.select_one("span.detail-name:contains('Property Type') ~ span.detail-value") else None,
                "year_built": int(prop_soup.select_one("span.detail-name:contains('Year Built') ~ span.detail-value").text.strip()) if prop_soup.select_one("span.detail-name:contains('Year Built') ~ span.detail-value") else None,
                "brokers": clean_brokers(
                    prop_soup.select_one("li:nth-of-type(1) div.name").text if prop_soup.select_one("li:nth-of-type(1) div.name") else None,
                    prop_soup.select_one("li:nth-of-type(2) div.name").text if prop_soup.select_one("li:nth-of-type(2) div.name") else None,
                    prop_soup.select_one("li:nth-of-type(3) div.name").text if prop_soup.select_one("li:nth-of-type(3) div.name") else None
                ),
                "start_bid": clean_price(prop_soup.select_one("span.detail-name:contains('Starting Bid') ~ span.detail-value").text) if prop_soup.select_one("span.detail-name:contains('Starting Bid') ~ span.detail-value") else None,
                "current_bid": None,
                "bid_increment": None,
                "bidding_starts": clean_date(prop_soup.select_one("span.date-formatted").text) if prop_soup.select_one("span.date-formatted") else None,
                "bidding_ends": None,
                "status": "in_progress",
                "size": clean_size(prop_soup.select_one("span.detail-name:contains('Square Footage') ~ span.detail-value").text) if prop_soup.select_one("span.detail-name:contains('Square Footage') ~ span.detail-value") else None
            }
            results.append(record)

        # Pagination
        next_btn = soup.select_one("a[aria-label='Next']")
        if next_btn and "href" in next_btn.attrs:
            driver.get("https://www.crexi.com" + next_btn["href"])
            time.sleep(3)
        else:
            break

    driver.quit()
    return results
