import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# Setup Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

# URLs to scrape
urls = ['https://nva.nielit.gov.in/', 'https://lms.nielit.gov.in/']

os.makedirs('output', exist_ok=True)
os.makedirs('pdfs', exist_ok=True)

def scroll_down_page():
    """ Scrolls down the page to load dynamic content """
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(20)  # Wait for more content to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def scrape_text_and_pdfs(url):
    driver.get(url)
    time.sleep(15)  # Wait for dynamic content to load
    
    scroll_down_page()  # Scroll to load all dynamic content

    # Extracting text data
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_data = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'a', 'span', 'div']):
        text_content = tag.get_text(strip=True)
        if text_content:
            text_data.append(text_content)
    
    # Save text data in order
    with open('output/data.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n\n=== {url} ===\n\n")
        f.write("\n".join(text_data))

    # Download PDFs
    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download')]")
    for link in pdf_links:
        pdf_url = link.get_attribute('href')
        if pdf_url and pdf_url.endswith('.pdf'):
            pdf_name = os.path.join('pdfs', pdf_url.split('/')[-1])
            if not os.path.exists(pdf_name):
                print(f"Downloading: {pdf_name}")
                response = requests.get(pdf_url)
                with open(pdf_name, 'wb') as pdf_file:
                    pdf_file.write(response.content)
                print(f"Downloaded: {pdf_name}")

# Start scraping
for url in urls:
    scrape_text_and_pdfs(url)

driver.quit()
