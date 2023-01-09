from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
import time
import os
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

db = mysql.connector.connect(
    host="localhost",
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database="CarDB"
)
cursor = db.cursor()

'''cursor.execute("SELECT * FROM CarModels ")
res = cursor.fetchall()
for row in res:
    print(row)'''

'''cursor.execute("SELECT * FROM CarListings ")
res = cursor.fetchall()
for row in res:
    print(row, "\n")'''

'''cursor.execute("SELECT COUNT(*) FROM CarDB.CarModels GROUP BY make")
res = cursor.fetchall()
print(res)
total = 0
for row in res:
    print(row[0])
    total += row[0]
print(total)'''

class FacebookBot:
    # Setup the bot
    def setup(self):
        chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument('--headless')
        chrome_options.add_argument("--disable-notifications")
        #chrome_options.add_experimental_option("prefs", { "profile.default_content_setting_values.notifications": 2 })
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        #self.driver.set_window_size(800, 600)

    # Close the bot
    def teardown(self):
        self.driver.close()

    # Run the bot
    def start_bot(self):
        FacebookBot.setup(self)
        FacebookBot.populate_makes_and_models_helper(self)
        FacebookBot.login(self)
        FacebookBot.populate_car_makes(self)
        FacebookBot.traverse_makes(self)
        FacebookBot.traverse_listings(self)
        FacebookBot.teardown(self)

    # Login to Facebook and navigate to the marketplace
    def login(self):
        driver = self.driver

        driver.get('https://www.facebook.com')

        username = WebDriverWait(driver, timeout=10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']")))
        username.clear()
        username.send_keys(os.getenv('FACEBOOK_USER'))

        password = WebDriverWait(driver, timeout=10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']")))
        password.clear()
        password.send_keys(os.getenv('FACEBOOK_PASSWORD'))

        login_button = WebDriverWait(driver, timeout=2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        login_button.click()
        time.sleep(1) # We are logged in!

        driver.get('https://www.facebook.com/marketplace/category/vehicles')
        time.sleep(1)

    # Open sub-menu, get each sub-menu element, then close sub-menu
    def populate_car_makes(self):
        driver = self.driver

        make_menu = WebDriverWait(driver, timeout=10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[9]/div[1]/div[1]/span/span')))
        make_menu.click()
        time.sleep(1)

        global car_makes
        car_makes = driver.find_element(
            By.XPATH, '//*[@id="seo_filters"]/div[2]/div[10]/div/div[1]').find_elements(By.XPATH, "*")

        make_menu = WebDriverWait(driver, timeout=5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[9]/div[1]/div[1]/span/span')))
        make_menu.click()

        #print(car_makes)
        #print(len(car_makes))

    # Gets additional car makes and models
    def populate_makes_and_models_helper(self):
        url = requests.get('https://www.kbb.com/car-make-model-list/new/view-all/model/')
        page = BeautifulSoup(url.text, "html.parser")
        model_list = page.find_all(class_="css-z687n ee33uo36")

        print("populating makes and models...")
        i = 3
        while True:
            if i >= len(model_list):
                break

            model = str(model_list[i])[32:-6]
            make = str(model_list[i+1])[32:-6]
            #print(model, make)

            cursor.execute("SELECT COUNT(*) FROM CarModels WHERE make LIKE %s AND model like %s", (make, model))
            added_models_cnt = cursor.fetchall()[0][0]
            #print("\t\tmatches of model found in db: ", added_models_cnt)

            if added_models_cnt > 0:  
                i += 3
                continue

            cursor.execute("INSERT IGNORE INTO CarModels (make, model) VALUES (%s, %s)", (make, model))
            
            i += 3
        db.commit()

    def traverse_makes(self):
        driver = self.driver

        print("populating still in progress...")
        global car_makes
        for i, make in enumerate(car_makes, start=1):
            try:
                driver.get('https://www.facebook.com/marketplace/category/vehicles')
                time.sleep(1)

                # Open current car make
                make_menu = WebDriverWait(driver, timeout=10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[9]/div[1]/div[1]/span/span')))
                make_menu.click()

                car_makes = driver.find_element(
                    By.XPATH, '//*[@id="seo_filters"]/div[2]/div[10]/div/div[1]').find_elements(By.XPATH, "*")
                car_makes[i].click()
                time.sleep(1)
                curr_make = car_makes[i].find_element(By.XPATH, './/span').get_attribute('innerHTML')
                #print(curr_make)

                make_menu = WebDriverWait(driver, timeout=5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[9]/div[1]/div[1]/span/span')))
                make_menu.click()

                # Get car make and models not included inside model database
                model_menu = WebDriverWait(driver, timeout=5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[11]/div[1]/div[1]/span/span')))
                model_menu.click()
                time.sleep(2.5)

                car_models = driver.find_element(
                    By.XPATH, '//*[@id="seo_filters"]/div[2]/div[12]/div/div[1]').find_elements(By.XPATH, "*")

                tmp_models = []
                for model in car_models:
                    tmp_models.append(model.text)
                car_models = tmp_models

                for model in car_models[1:]:
                    cursor.execute("SELECT COUNT(*) FROM CarModels WHERE make LIKE %s AND model LIKE %s", (curr_make, model))
                    added_models_cnt = cursor.fetchall()[0][0]
                    #print("\t\tmatches of model found in db: ", added_models_cnt)

                    if added_models_cnt > 0:  
                        continue
                    cursor.execute("INSERT IGNORE INTO CarModels (make, model) VALUES (%s, %s)", (curr_make, model))
                db.commit()
                print("done!\n")

                print(curr_make)
                print(car_models)
                #print(len(car_models))

                model_menu = WebDriverWait(driver, timeout=5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[11]/div[1]/div[1]/span/span')))
                model_menu.click()

                print("populating new listings...")
                # Change sellers to individual
                change_seller = WebDriverWait(driver, timeout=5).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[3]/div[1]/div[1]/span/span')))
                change_seller.click()

                change_seller = WebDriverWait(driver, timeout=5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="seo_filters"]/div[2]/div[4]/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/span')))
                change_seller.click()
                time.sleep(1)

                change_seller = WebDriverWait(driver, timeout=5).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="seo_filters"]/div[2]/div[3]/div[1]/div[1]/span/span')))
                change_seller.click()

                # Scroll to the end of the page and get make listings
                page_height = driver.execute_script("return document.body.scrollHeight") 
                while True:
                    #print(page_height)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                    time.sleep(2)
                    if driver.execute_script("return document.body.scrollHeight") == page_height:
                        car_listings = driver.find_elements(
                            By.CSS_SELECTOR, 'a.x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1heor9g.x1lku1pv')
                        break
                    page_height = driver.execute_script("return document.body.scrollHeight")
                print("checking", len(car_listings), "listings")

                # Append new listings to the database
                for listing in car_listings:
                    link_key = "%" + listing.get_attribute('Href')[12:59] + "%"
                    #print(listing.text)
                    listing_cnt = cursor.execute("SELECT COUNT(*) FROM CarListings WHERE link LIKE %s", (link_key,))
                    listing_cnt = cursor.fetchall()[0][0]
                    #print("\tmatches of listing found in db: ", listing_cnt)

                    if listing_cnt > 0 or 'notif' in listing.get_attribute('Href'):
                            continue
                            
                    listing_link = listing.get_attribute('Href')[:listing.get_attribute('Href').index('/?hoisted')]
                    cursor.execute(
                        "INSERT IGNORE INTO CarListings (make, link) VALUES (%s, %s)", (curr_make, listing_link))
            except:
                continue
            db.commit()

    def traverse_listings(self):
        driver = self.driver

        # Get new listings from the database
        get_listings = cursor.execute("SELECT link FROM CarListings WHERE listing_name IS NULL")
        get_listings = cursor.fetchall()
        listings = []
        for listing in get_listings:
            listings.append(listing[0])
        #print(listings)

        for listing_url in listings:
            driver.get(listing_url)
            time.sleep(1)
            #open("tmp3.txt", "w").write(driver.page_source)
            content = driver.page_source

            # Extract and format the data
            try:
                description = content[content.index('"text":"')+len('"text":"'):content.index('"},"creation_time"')]
                description = description.replace("\\n", "\n").replace("\\", "").replace("u00b7", "-").replace("ud83dudccd", "")
                description = description.replace("u2019", "'").replace("u201d", '"').replace("u27a1ufe0f", "->")
                description = description.replace("ud83dudc49ud83cudffc", "->").replace("ud83dudc49ud83cudffcSi", "->")
                description = description.replace("ud83dudc49ud83cudffbIf", "->").replace("ud83dudc49ud83cudffb", "->")
                description = description.replace("u00ed", "i").replace("u00e9", "e").replace("u0040", "@").replace("u00da", "U")
                description = description.replace("ud83dude97", "").replace("ud83dudcaf", "").replace("ud83dude98", "")
                description = description.replace("u2757ufe0fu2757ufe0fu2757ufe0f", "!").replace("ud83dudd34", "")
                description = description.replace("ud83dudcb0", "$").replace("ud83dudc4dud83cudffb", "").replace("u00f3", "o")
                description = description.replace("ud83dudce2", "").replace("ud83dudc4f", "").replace("ud83dudc4f", "")
                description = description.replace("ud83dudc41", "-").replace("ud83dudcf1", "").replace("ud83eudd1dud83cudffc", "")
                description = description.replace("ud83cudde7ud83cuddf7", "").replace("ud83dudcf1", "").replace("u00e1", "a")
                description = description.replace("ud83dudcdd", "").replace("ud83dudcf2", "").replace("ud83dudc4c", "")
                description = description.replace("u00c9", "E").replace("ufffc", "").replace("u2026", "...")
                description = description.replace("u26a1ufe0f", "")

                try:
                    description = description[:description.index("[hidden information]")]
                except:
                    pass
                try:
                    description = description[:description.index('"},"id":')]
                except:
                    pass
            except:
                description = None

            try:
                post_date = content[content.index('"creation_time":')+len('"creation_time":'):content.index(',"location_text"')]
                post_date = datetime.fromtimestamp(int(post_date)).strftime("%m/%d/%Y")
            except:
                post_date = None

            accessed_date = datetime.now().strftime("%m/%d/%Y")

            try:
                location = content[content.index('"location_text":')+len('"location_text":{"text":"'):content.index('"},"location_vanity_or_id"')]
                city = location[:-4]
                state = location[-2:]
            except:
                city = None
                state = None

            try:
                price = content[content.index('"amount":')+len('"amount":"'):content.index('"},"__isMarketplaceVehicleListing"')]
                price = float(price)
            except:
                price = None

            try:
                condition = content[content.index('"condition":')+len('"condition":"'):content.index('","custom_title"')]
                if condition == 'PC_USED_GOOD':
                    condition = 'USED'
            except:
                condition = None

            try:
                title = content[content.index('"custom_title":')+len('"custom_title":"'):content.index('","is_live"')]
                try:
                    year = title[:4]
                    year = int(year)
                except:
                    year = None
            except:
                title = None

            try:
                color = content[content.index('"vehicle_interior_color":')+len('"vehicle_interior_color":"'):content.index('","vehicle_is_paid_off"')]
            except:
                color = None

            try:
                vin = content[content.index('"vehicle_identification_number":')+len('"vehicle_identification_number":"'):content.index('","vehicle_interior_color"')]
            except:
                vin = None

            try:
                make = content[content.index('"vehicle_make_display_name":')+len('"vehicle_make_display_name":"'):content.index('","vehicle_model_display_name"')]
            except:
                make = None

            try:
                model = content[content.index('"vehicle_model_display_name"')+len('"vehicle_model_display_name":"'):content.index('","vehicle_number_of_owners":')]
            except:
                model = None

            try:
                miles = content[content.index('"vehicle_odometer_data":')+len('"vehicle_odometer_data":{"unit":"MILES","value":'):content.index('},"vehicle_registration_plate_information"')]
                miles = int(miles)
            except:
                miles = None

            try:
                title_status = content[content.index('"vehicle_title_status":')+len('"vehicle_title_status":"'):content.index('","vehicle_transmission_type"')]
            except:
                title_status = None

            try:
                transmission = content[content.index('"vehicle_transmission_type":')+len('"vehicle_transmission_type":"'):content.index('","vehicle_trim_display_name"')]
            except:
                transmission = None

            print(description, "\n")
            print("post_date:", post_date, "accessed_date:", accessed_date)
            print("city:", city, "state:", state, "price:", price, "condition:", condition, "title:", title, "year:", year) 
            print("color:", color, "vin:", vin, "make:", make, "model:", model, "miles:", miles, "title:", title_status,"trans:", transmission)
            print(listing_url, "\n\n")

            # Insert into db
            '''cursor.execute(
                "UPDATE CarListings SET vehicle_year=%s, make=%s, model=%s, listing_name=%s, vehicle_condition=%s, title_status=%s, listed_price=%s, exterior_color=%s, mileage=%s, transmission=%s, city=%s, state=%s, vehicle_identification_number=%s, seller_description=%s WHERE link LIKE %s", 
                (year, make, model, title, condition, title_status, price, color, miles, transmission, city, state, vin, description, listing))
        db.commit()'''
        