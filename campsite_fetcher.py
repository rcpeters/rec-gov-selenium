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
parser.add_argument("--startDate", required=True, help="reservations start date")
parser.add_argument("--endDate", required=True, help="reservations start date")
parser.add_argument("--resTime", required=True, help="reservations for time res open hh:mm:ss in localtime of machine")
parser.add_argument("--username", required=True, help="username", env_var="REC_GOV_USER")
parser.add_argument("--password", required=True, help="password", env_var="REC_GOV_PASS")
parser.add_argument("--campIds", required=True, help="list of campsites by ids")

args = parser.parse_args()

class CampsiteFetcher():
  def setup(self, args):
    o = webdriver.ChromeOptions()
    o.add_experimental_option("detach", True)
    # Code to use profile which might come in handy later
    #o.add_argument('profile-directory=Profile 3')
    #o.add_argument('user-data-dir=C:\\Users\\info\\AppData\\Local\\Google\\Chrome\\User Data')
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
    rTimeStr = args.resTime.split(':')
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
    self.driver.find_element(By.ID, "startDate").send_keys(args.startDate)
    self.driver.find_element(By.ID, "endDate").click()
    self.driver.find_element(By.ID, "endDate").clear()
    self.driver.find_element(By.ID, "endDate").send_keys(args.endDate)
    self.driver.find_element(By.CSS_SELECTOR, ".nav-search-button").click()
    WebDriverWait(self.driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//div[@class='search-pagination-text']"))
    )
    
    campsites = args.campIds.split(",")
    foundSite = False
    finalLoop = False
    
    for campsite in  campsites:
      self.driver.switch_to.new_window('tab')
      self.driver.get("https://www.recreation.gov/camping/campsites/" + campsite)
    for handle in self.driver.window_handles[1:]:
        # by check price we can know if page has loaded
        self.driver.switch_to.window(handle)
        WebDriverWait(self.driver, 10).until(
          EC.visibility_of_element_located((By.XPATH, "//div[@class='book-bar-price']/span[not(contains(.,'$0.00'))]"))
        )

    pause.until(resDatetime)

    while (finalLoop == False):
      # if found site set final loop (one more pass)
      if (foundSite==True): 
        finalLoop = True
      
      # click all adds site first
      for handle in self.driver.window_handles[1:]:
        self.driver.switch_to.window(handle)
        addEl = self.driver.find_element(By.ID, "add-cart-campsite")
        if addEl.is_enabled():
          addEl.click()
        while self.driver.find_elements(By.XPATH, "//h1[contains(@data-component, 'Heading') and contains(., 'Booking Reservation')]"):
          None

      # check and see if the page says 'Continue Shopping' or  'Proceed with Reservation'
      for handle in self.driver.window_handles[1:]:
          self.driver.switch_to.window(handle)
          # what until we know if "Proceed with Reservation" or "Continue Shopping"
          # is available

          # click "Proceed with Reservation" if it exist
          proceedEls = self.driver.find_elements(By.XPATH, "//Button[contains(@class, 'sarsa-button') and contains(., 'Proceed with Reservation')]")
          if proceedEls:
            proceedEls[0].click()

          continueEls = self.driver.find_elements(By.XPATH, "//Button[contains(@class, 'sarsa-button') and contains(., 'Continue Shopping')]")
          if continueEls:
            continueEls[0].click()
            foundSite=True
            self.driver.close()

      # see if we should wait or refresh
      for handle in self.driver.window_handles[1:]:
        self.driver.switch_to.window(handle)
        bookingH1 = self.driver.find_elements(By.XPATH, "//h1[contains(@data-component, 'Heading') and contains(., 'Booking Reservation')]")
        if not bookingH1:
          self.driver.refresh()
    
  
tkc = CampsiteFetcher()
tkc.setup(args)
tkc.get_sites(args)