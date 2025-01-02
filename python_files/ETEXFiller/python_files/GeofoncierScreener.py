from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os

class GeofoncierScreener:
    def __init__(self):
        pass

    def get_pic(self,path,idu):
        url = f"https://public.geofoncier.fr/?utm_source=geofoncier.fr&utm_medium=Referral&utm_campaign=btn-menu-public&parcelle={idu}"

        # Set up the WebDriver (Chrome in this case)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run browser in headless mode (no GUI)
        options.add_argument("--window-size=1920,1080")  # Set the browser window size

        # Create the WebDriver instance
        driver = webdriver.Chrome(options=options)

        try:
            # Open the GeoFoncier website
            driver.get(url)

            # Wait for the page to load fully
            time.sleep(0.5)  # You can use WebDriverWait for a more robust solution
            web_elem = driver.find_element(By.CLASS_NAME, "leaflet-popup-close-button")
            web_elem.click()
            time.sleep(0.2)
            web_elem = driver.find_element(By.CLASS_NAME, "leaflet-control-fullscreen-button.leaflet-bar-part")
            web_elem.click()
            time.sleep(0.3)

            # Take a screenshot and save it to a file

            driver.save_screenshot(path)

            print(f"Screenshot saved successfully: {path}")

        finally:
            # Close the browser
            driver.quit()
