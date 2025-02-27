import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor

visited_urls = set()

def crawl(url, depth=2):
    if depth == 0 or url in visited_urls:
        return
    visited_urls.add(url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link['href'])
            if new_url.startswith(url):
                crawl(new_url, depth-1)

        for form in soup.find_all("form"):
            print(f"Form found at {url}")
    except requests.exceptions.RequestException as e:
        print(f"Error crawling {url}: {e}")

def check_robots(url):
    robots_url = urljoin(url, "/robots.txt")
    try:
        response = requests.get(robots_url)
        response.raise_for_status()
        print(f"Robots.txt:\n{response.text}")
    except requests.exceptions.RequestException:
        print("No robots.txt found")

def crawl_dynamic(url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(url)
        page_source = driver.page_source
    finally:
        driver.quit()
    return page_source

def request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException:
            print(f"Retrying ({attempt+1}/{max_retries})...")
            time.sleep(2)
    print("Failed after retries.")
    return None

def extract_forms(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        forms = soup.find_all("form")
        for form in forms:
            inputs = form.find_all("input")
            print(f"Form found at {url} with fields {[i['name'] for i in inputs if i.has_attr('name')]}")
    except requests.exceptions.RequestException as e:
        print(f"Error extracting forms from {url}: {e}")

def store_url(url, cursor, conn):
    cursor.execute("INSERT INTO urls (url) VALUES (?)", (url,))
    conn.commit()

def crawl_multithreaded(urls):
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(crawl, urls)

def main():
    conn = sqlite3.connect('crawler.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT)")
    conn.commit()

    try:
        crawl("https://example.com")
        check_robots("https://www.google.com")
        print(crawl_dynamic("https://example.com"))
        extract_forms("https://example.com")
        store_url("https://example.com", cursor, conn)
        crawl_multithreaded(["https://example1.com", "https://example2.com"])
    finally:
        conn.close()

if __name__ == "__main__":
    main()
