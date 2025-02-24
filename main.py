import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
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

def scrape_text_and_pdfs(url):
    driver.get(url)
    time.sleep(10)  

    # Extracting text data
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_data = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'a', 'span', 'div']):
        text_content = tag.get_text(strip=True)
        if text_content:
            text_data.append(text_content)
    
    with open('output/data.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n\n=== {url} ===\n\n")
        f.write("\n".join(text_data))

    # Download PDFs
    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
    for link in pdf_links:
        pdf_url = link.get_attribute('href')
        if pdf_url:
            pdf_name = os.path.join('pdfs', pdf_url.split('/')[-1])
            if not os.path.exists(pdf_name):
                response = requests.get(pdf_url)
                with open(pdf_name, 'wb') as pdf_file:
                    pdf_file.write(response.content)
                print(f"Downloaded: {pdf_name}")

# Start scraping
for url in urls:
    scrape_text_and_pdfs(url)

driver.quit()
