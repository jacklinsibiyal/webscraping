import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from urllib.parse import urljoin
from webdriver_manager.chrome import ChromeDriverManager
import re
from fpdf import FPDF
import pdfplumber
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

options = webdriver.ChromeOptions()
options.add_argument('--headless')  
options.add_argument('--no-sandbox')
options.add_argument("--disable-gpu")
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

urls = ['https://nva.nielit.gov.in/', 'https://lms.nielit.gov.in/']
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

os.makedirs('output', exist_ok=True)
os.makedirs('pdfs', exist_ok=True)
os.makedirs('vector_store', exist_ok=True)

def scroll_down_page():
    """ Scrolls down the page to load dynamic content """
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def download_pdf(pdf_url):
    """ Downloads the PDF from the given URL and triggers vector embedding """
    if pdf_url and pdf_url.endswith('.pdf'):
        pdf_name = os.path.join('pdfs', pdf_url.split('/')[-1])
        if not os.path.exists(pdf_name):
            print(f"Downloading: {pdf_name}")
            try:
                response = requests.get(pdf_url)
                response.raise_for_status() 
                with open(pdf_name, 'wb') as pdf_file:
                    pdf_file.write(response.content)
                print(f"Downloaded: {pdf_name}")
                vector_embedding()

            except Exception as e:
                print(f"Failed to download {pdf_url}: {e}")
        else:
            print(f"Already downloaded: {pdf_name}")

def text_to_pdf(text_file, pdf_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)

    with open(text_file, 'r', encoding='utf-8') as file:
        re.sub(r'[^\x00-\x7F]+', '', file.read())
        for line in file:
            pdf.multi_cell(0, 10, line, align='L')
    
    pdf.output(pdf_file)
    print(f"Converted {text_file} to {pdf_file}")

    # Delete the text file after converting to PDF
    os.remove(text_file)
    print(f"Deleted the text file: {text_file}")

def scrape(url):
    driver.get(url)
    time.sleep(15) 
    
    scroll_down_page() 
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_data = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'a', 'span', 'div']):
        text_content = tag.get_text(strip=True)
        if text_content:
            text_data.append(text_content)
    text_file = f'pdfs/{url.split("/")[-1]}.txt'

    with open(text_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n=== {url} ===\n\n")
        f.write("\n".join(text_data))
        f.write("\n" + "="*50 + "\n")
    pdf_file = f'pdfs/{url.split("/")[-1]}.pdf'
    text_to_pdf(text_file, pdf_file)
    links = soup.find_all('a')
    print(f"Found {len(links)} anchor tags on {url}")

    pattern = r"window\.open\(['\"](.*?)['\"]\)"
    
    for index, link in enumerate(links):
        try:
            onclick_attr = link.get('onclick')
            if onclick_attr:
                matches = re.findall(pattern, onclick_attr)
                if matches:
                    for relative_url in matches:
                        full_url = urljoin(url, relative_url)
                        print(f"Constructed PDF URL: {full_url}")
                        if full_url.endswith('.pdf'):
                            download_pdf(full_url)
                        else:
                            print(f"Constructed URL is not a PDF: {full_url}")
                else:
                    print("No matching URL found in 'onclick' attribute.")
            else:
                print("No 'onclick' attribute found.")
        
        except Exception as e:
            print(f"Error processing link {index + 1}: {e}")

def vector_embedding():
    """ Vectorizes documents and saves vectors to disk """
    try:
        if os.path.exists("vector_store/faiss_index"):
            print("✅ Vector Store DB Loaded from Disk!")
            return

        print("🚀 Starting Vector Embedding Process...")

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        docs = []

        pdf_files = os.listdir("./pdfs")
        for pdf_file in pdf_files:
            file_path = f"./pdfs/{pdf_file}"
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
            if text:
                text_document = Document(page_content=text, metadata={"source": pdf_file})
                docs.append(text_document)
            else:
                print(f"⚠️ No text extracted from: {pdf_file}")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        final_documents = text_splitter.split_documents(docs[:])
        vectors = FAISS.from_documents(final_documents, embeddings)
        vectors.save_local("vector_store/faiss_index")
        print("✅ Vector Store DB Is Ready and Saved Locally!")

    except Exception as e:
        print(f"Error in vector embedding: {e}")
for url in urls:
    scrape(url)

driver.quit()
print("Scraping and Vector Embedding completed.")