import requests
from requests.exceptions import RequestException

def make_request(url):
    """Safely makes a GET request and returns the response."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except RequestException as e:
        print(f"Request failed: {e}")
        return None

def clean_text(text):
    """Cleans text by stripping whitespace and handling special characters."""
    return text.strip() if text else ""
