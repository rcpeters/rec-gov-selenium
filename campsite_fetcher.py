import pytest
import sys
import time
import json
import configargparse
from datetime import datetime, timedelta
import pause
#from selenium import webdriver
from seleniumwire import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
#from selenium_stealth import stealth

parser = configargparse.ArgumentParser()
parser.add_argument("--start_date", required=True, help="reservations start date")
parser.add_argument("--end_date", required=True, help="reservations start date")
parser.add_argument("--res_time", required=True, help="reservations for time res open hh:mm:ss in localtime of machine")
parser.add_argument("--username", required=True, help="username", env_var="REC_GOV_USER")
parser.add_argument("--password", required=True, help="password", env_var="REC_GOV_PASS")
parser.add_argument("--camp_ids", required=True, help="list of campsites by ids")
parser.add_argument('--detach', default=True ,type=lambda x: not (str(x).lower() == 'false'))
parser.add_argument("--g_profile", help="Google Chrome profile", env_var="G_PROFILE")
parser.add_argument("--g_user_data_dir", help="Google User Data", env_var="G_USER_DATA")

args = parser.parse_args()

now = datetime.now()
rTimeStr = args.res_time.split(':')
resDatetime = datetime.now().replace(hour=int(rTimeStr[0]),minute=int(rTimeStr[1]),second=int(rTimeStr[2]),microsecond=0)
loginDatetime = resDatetime - timedelta(minutes=2)
print(f"current time {datetime.now()}")
print(f"login time {loginDatetime}")
print(f"reservation time {resDatetime}")

pause.until(loginDatetime)

def interceptor(request):  # A response interceptor takes two args
    if request.url.startswith('https://www.recreation.gov/api/camps/reservations/campgrounds/'):
        # pause until it's registration time
        pause.until(resDatetime)
        print(request.url)

class CampsiteFetcher():
  def setup(self, args):
    o = webdriver.ChromeOptions()

    if args.detach:
         o.add_experimental_option("detach", True)
    if args.g_profile:
        o.add_argument('profile-directory=' + args.g_profile)
    if args.g_user_data_dir:
        o.add_argument('user-data-dir=' + args.g_user_data_dir)
    service = ChromeService(executable_path=ChromeDriverManager().install())
    
    self.driver = webdriver.Chrome(service=service,options=o)
    self.driver.request_interceptor = interceptor

    # stealth seems to only be used for preventing detecting headless
    #stealth(self.driver,
    #    languages=["en-US", "en"],
    #    vendor="Google Inc.",
    #    platform="Win32",
    #    webgl_vendor="Intel Inc.",
    #    renderer="Intel Iris OpenGL Engine",
    #    fix_hairline=True,
    #    )

    self.driver.set_page_load_timeout(100)
    self.vars = {}
  
  def teardown_method(self, method):
    #self.driver.quit()
    None
  
  def get_sites(self, args):

    self.driver.get("https://www.recreation.gov/search")
    self.driver.set_window_size(1400, 800)

    
    WebDriverWait(self.driver, 10).until(
        EC.element_to_be_clickable(self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Log In')]"))
    )
    self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Log In')]").click()
    

    WebDriverWait(self.driver, 10).until(
        EC.element_to_be_clickable(self.driver.find_element(By.ID, "email"))
    )
    self.driver.find_element(By.ID, "email").click()
    self.driver.find_element(By.ID, "email").send_keys(args.username)
    self.driver.find_element(By.ID, "rec-acct-sign-in-password").click()
    self.driver.find_element(By.ID, "rec-acct-sign-in-password").send_keys(args.password)
    
    self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
    WebDriverWait(self.driver, 10).until(
        EC.invisibility_of_element((By.XPATH, "//button[@type='submit']"))
    )


    WebDriverWait(self.driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@aria-label, 'month, Start Date, ')]"))
    )
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, Start Date, ')]").click()
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, Start Date, ')]").clear()
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, Start Date, ')]").send_keys(args.start_date)
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, End Date, ')]").click()
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, End Date, ')]").clear()
    self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'month, End Date, ')]").send_keys(args.end_date)

    #<div class="rec-flex-card-image-wrap"><div data-component="Placeholder" style="height: 100px;"></div></div>
    WebDriverWait(self.driver, 10).until(
        EC.invisibility_of_element((By.XPATH, "//div[contains(@data-component, 'Placeholder')]"))
    )
    
    campsites = args.camp_ids.split(",")
    handlesDict = {}
    
    for campsite in campsites:
      self.driver.switch_to.new_window('tab')
      self.driver.get("https://www.recreation.gov/camping/campsites/" + campsite)
      handlesDict[campsite]=self.driver.current_window_handle
    for campsite, handle in handlesDict.items():
        # check price we can know if page has loaded
        self.driver.switch_to.window(handle)
        WebDriverWait(self.driver, 10).until(
          EC.visibility_of_element_located((By.XPATH, '//h2[@data-component="Heading" and @class="h5-normal" and string-length() > 0]'))
        )
        print(campsite + " loaded")

      
    # click all adds site first
    for campsite, handle in handlesDict.items():
        self.driver.switch_to.window(handle)
        addEls = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Add')]")
        if addEls:
            if addEls[0].is_enabled():
                addEls[0].click()
                print(campsite + " clicked add")
                proceedBtn = self.driver.find_elements(By.XPATH, "//Button[contains(@class, 'sarsa-button') and contains(., 'Proceed with Reservation')]")
                if proceedBtn:
                  proceedBtn[0].click()
                while self.driver.find_elements(By.XPATH, "//h1[contains(@data-component, 'Heading') and contains(., 'Booking Reservation')]"):
                  None # loop until Booking Reservations goes away, rec.gov will ony allow one inflight booking request

    # see if we should wait or refresh, or close
    for campsite, handle in handlesDict.items():
        self.driver.switch_to.window(handle)
        WebDriverWait(self.driver, 10).until(
          EC.visibility_of_element_located((By.XPATH, '//h2[@data-component="Heading" and @class="h5-normal" and string-length() > 0]'))
        )
        reservedBtn = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Reserved')]")
        unavailableBtn = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Unavailable')]")
        if reservedBtn:
            print(campsite + " already reserved")
            self.driver.close()
        elif unavailableBtn:
            print(campsite + " unavailable to reserve")
            self.driver.close()
        elif "orderdetails" in self.driver.current_url:
            print(campsite + " BOOKED!")
            self.driver.close()

    self.driver.switch_to.window(self.driver.window_handles[0])
    self.driver.get("https://www.recreation.gov/cart")

tkc = CampsiteFetcher()
tkc.setup(args)
tkc.get_sites(args)

# keep python running until I hit enter
print("press enter to end already reserved")
input() 