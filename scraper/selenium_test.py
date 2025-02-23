from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import urllib.parse

chrome_driver_path = "/opt/homebrew/bin/chromedriver"  # Update if different

chrome_options = Options()
keywords = ["frontend", "backend", "data science"]
# Start ChromeDriver
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

for keyword in keywords:
    encoded_role = urllib.parse.quote_plus(keyword)
    # Open the Indeed job listings page
    driver.get("https://sg.indeed.com/jobs?q={}&fromage=1&sc=0kf%3Aattr%28VDTG7%29%3B".format(encoded_role))

    # Wait until the job listings are loaded
    job_cards = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.css-1ac2h1w"))
    )

    # Loop through each job card and extract details
    for card in job_cards:
        try:
            # Extract job title from the <h2> element's nested <a> tag
            job_title = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a").get_attribute("title")
            
            # Extract company name using its data-testid attribute
            company = card.find_element(By.CSS_SELECTOR, "span[data-testid='company-name']").text
            
            # Extract job location using its data-testid attribute
            location = card.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']").text
            
            print("Job Title:", job_title)
            print("Company:", company)
            print("Location:", location)
            print("-" * 40)
        except Exception as e:
            print("Error extracting data from a job card:", e)

# Close the driver once done
driver.quit()