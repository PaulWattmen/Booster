import json
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
import time
import os

class RteFormFiller:

    def __init__(self, params_json_path):
        with open(params_json_path, "r") as file:
            self.params = json.load(file)
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
        options = webdriver.ChromeOptions()
        options.add_argument("--user-data-dir="+os.path.join(local_dir,"selenium_chrome_session"))
        # options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(options=options)

    def open_form(self):
        url = "https://www.services-rte.com/home/publique/decouvrez-nos-services-dacces-au/raccorder-une-installation-de-pr/realiser-une-demande-d-etude-exp.html"
        self.driver.get(url)
        if self.driver.current_url != url:
            return -1

    def manipulate_date_board(self):
        self.driver.find_element(By.ID, "mat-input-12").click()
        time.sleep(0.3)
        web_elem = self.driver.find_element(By.XPATH, "//img[@src='assets-cortex/icons/thin-arrow-right.svg']")
        for x in range(0, 16):
            web_elem.click()
            time.sleep(0.1)
        self.driver.find_element(By.CLASS_NAME, "mat-calendar-body-cell").click()

    def fill_form(self,plot_attributes):
        for elem in self.params["list"]:
            if elem["id"]:
                web_elem = self.driver.find_element(By.ID, elem["id"])
            elif elem["class"]:
                web_elem = self.driver.find_element(By.CLASS_NAME, elem["class"])
            else:
                continue
            #print(web_elem.get_attribute("class"))
            if elem["action"] == "click":
                web_elem.click()

            elif elem["action"] == "write_from_data":
                for attr in plot_attributes.keys():
                    if attr in elem["name"]:
                        web_elem.send_keys(plot_attributes[attr])

            elif elem["action"] == "calendar":
                self.manipulate_date_board()

            elif elem["action"] == "write":
                web_elem.send_keys(elem["value"])
            time.sleep(0.3)
            if "Suivant" in elem["name"]:
                time.sleep(0.4)
                self.driver.execute_script("window.scrollTo(0, 70);", "")

        #input("Appuyez sur ENTREE pour fermer la fenêtre du navigateur et terminer ce script : ")
        #self.driver.quit()