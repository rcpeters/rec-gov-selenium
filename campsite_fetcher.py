import pytest
import sys
import time
import json
import configargparse
from datetime import datetime, timedelta
import pause
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC

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
    self.driver.set_page_load_timeout(10)
    self.vars = {}
  
  def teardown_method(self, method):
    #self.driver.quit()
    None
  
  def wait_for_window(self, timeout = 2):
    time.sleep(round(timeout / 1000))
    wh_now = self.driver.window_handles
    wh_then = self.vars["window_handles"]
    if len(wh_now) > len(wh_then):
      return set(wh_now).difference(set(wh_then)).pop()
  
  def get_sites(self, args):

    now = datetime.now()
    rTimeStr = args.res_time.split(':')
    resDatetime = datetime.now().replace(hour=int(rTimeStr[0]),minute=int(rTimeStr[1]),second=int(rTimeStr[2]),microsecond=0)
    loginDatetime = resDatetime - timedelta(minutes=2)
    print(loginDatetime)
    print(resDatetime)
    print(datetime.now())
    pause.until(loginDatetime)

    self.driver.get("https://www.recreation.gov/")
    self.driver.set_window_size(1400, 800)

    self.driver.find_element(By.XPATH, "//button[@aria-label='Log In']").click()
    self.driver.find_element(By.ID, "email").send_keys(args.username)
    self.driver.find_element(By.ID, "rec-acct-sign-in-password").send_keys(args.password)
    self.driver.find_element(By.ID, "email").click()
    self.driver.find_element(By.XPATH, "//button[@type='submit' and @aria-label='Log In']").click()
    
    self.driver.find_element(By.XPATH, "//div[contains(text(),'Camping & Lodging')]").click()
    self.driver.find_element(By.ID, "startDate").click()
    self.driver.find_element(By.ID, "startDate").clear()
    self.driver.find_element(By.ID, "startDate").send_keys(args.start_date)
    self.driver.find_element(By.ID, "endDate").click()
    self.driver.find_element(By.ID, "endDate").clear()
    self.driver.find_element(By.ID, "endDate").send_keys(args.end_date)
    self.driver.find_element(By.CSS_SELECTOR, ".nav-search-button").click()
    WebDriverWait(self.driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//div[@class='search-pagination-text']"))
    )
    
    campsites = args.camp_ids.split(",")
    
    for campsite in  campsites:
      self.driver.switch_to.new_window('tab')
      self.driver.get("https://www.recreation.gov/camping/campsites/" + campsite)
    for handle in self.driver.window_handles[1:]:
        # check price we can know if page has loaded
        self.driver.switch_to.window(handle)
        WebDriverWait(self.driver, 10).until(
          EC.visibility_of_element_located((By.XPATH, '//h2[@data-component="Heading" and @class="h5-normal" and string-length() > 0]'))
        )

    pause.until(resDatetime)

      
    # click all adds site first
    for handle in self.driver.window_handles[1:]:
        self.driver.switch_to.window(handle)
        addEls = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Add')]")
        if addEls:
            if addEls[0].is_enabled():
                addEls[0].click()
        while self.driver.find_elements(By.XPATH, "//h1[contains(@data-component, 'Heading') and contains(., 'Booking Reservation')]"):
            None # loop until Booking Reservations goes away, rec.gov will ony allow one inflight booking request

    # check and see if the page says 'Continue Shopping' or  'Proceed with Reservation'
    for handle in self.driver.window_handles[1:]:
        self.driver.switch_to.window(handle)
        # what until we know if "Proceed with Reservation" or "Continue Shopping"
        # is available

        # click "Proceed with Reservation" if it exist
        proceedBtn = self.driver.find_elements(By.XPATH, "//Button[contains(@class, 'sarsa-button') and contains(., 'Proceed with Reservation')]")
        if proceedBtn:
            proceedBtn[0].click()

    # not sure we have to do this
    #  continueBtn = self.driver.find_elements(By.XPATH, "//Button[contains(@class, 'sarsa-button') and contains(., 'Continue Shopping')]")
    # if continueBtn:
    #    continueBtn[0].click()
    #    self.driver.close()

    # see if we should wait or refresh, or close
    for handle in self.driver.window_handles[1:]:
        self.driver.switch_to.window(handle)
        print(handle)
        WebDriverWait(self.driver, 10).until(
          EC.visibility_of_element_located((By.XPATH, '//h2[@data-component="Heading" and @class="h5-normal" and string-length() > 0]'))
        )
        reservedBtn = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Reserved')]")
        unavailableBtn = self.driver.find_elements(By.XPATH, "//Button[@id='add-cart-campsite' and contains(., 'Unavailable')]")
        bookingH1 = self.driver.find_elements(By.XPATH, "//h1[contains(@data-component, 'Heading') and contains(., 'Booking Reservation')]")
        if reservedBtn or unavailableBtn:
            self.driver.close()
        elif not bookingH1:
            self.driver.refresh()
     
tkc = CampsiteFetcher()
tkc.setup(args)
tkc.get_sites(args)