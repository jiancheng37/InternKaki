import logging
from .utils import clean_text, make_request

# Define what gets exposed when using `from scraper import *`
__all__ = ["scrape_internsg", "clean_text", "make_request"]

# Configure logging (applies to all scrapers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/scraper.log"),  # Saves logs to a file
        logging.StreamHandler()  # Displays logs in the console
    ]
)
