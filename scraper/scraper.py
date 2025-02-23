import logging
from bs4 import BeautifulSoup
from .utils import clean_text, make_request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib


def scrape_internsg(keywords):
    """Scrapes InternSG for internships based on user keywords."""
    base_url = "https://www.internsg.com/jobs/?f_0=1&f_p=&f_i=&filter_s={}"
    internships = []

    for keyword in keywords:
        encoded_keyword = urllib.parse.quote_plus(keyword)
        url = base_url.format(encoded_keyword)
        logging.info(f"🔍 Scraping InternSG for keyword: {keyword}")

        response = make_request(url)

        if response.status_code != 200:
            logging.error(f"❌ Failed to fetch {url} - Status Code: {response.status_code}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        job_listings = soup.select(".ast-row.list-odd, .ast-row.list-even")

        logging.info(f"📌 Found {len(job_listings)} job listings for keyword: {keyword}")

        for job in job_listings:
            try:
                # Extract company name
                company = clean_text(job.select_one(".ast-col-lg-3").text.split("\n")[0])

                # Extract job title and link
                job_title_tag = job.select_one(".ast-col-lg-3 a")
                title = clean_text(job_title_tag.text)
                raw_link = job_title_tag['href']
                clean_link = raw_link.split("?")[0]

                # Extract location
                location = clean_text(job.select(".ast-col-lg-2 .job-listing-dt")[0].text)

                # Extract job duration
                duration = clean_text(job.select(".ast-col-lg-3 .job-listing-dt")[0].text)

                # Extract job posting date
                post_date = clean_text(job.select(".ast-col-lg-1 span")[0].text)

                internships.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "duration": duration,
                    "post_date": post_date,
                    "link": clean_link
                })

                logging.info(f"✅ Scraped job: {title} at {company}")

            except AttributeError as e:
                logging.warning(f"⚠️ Skipping job due to missing fields: {e}")
                continue  # Skip job listings that are missing required fields

    logging.info(f"✅ Scraping completed! {len(internships)} internships found.")
    return internships

def scrape_indeed(keywords):

    chrome_driver_path = "/opt/homebrew/bin/chromedriver"  # Update if different

    chrome_options = Options()

    # Start ChromeDriver
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Open the Indeed job listings page
    driver.get("https://www.indeed.com/jobs?q=your+search+query")

    # Wait until the job listings are loaded
    job_cards = WebDriverWait(driver, 15).until(
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
