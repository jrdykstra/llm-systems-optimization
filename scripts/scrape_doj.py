"""Scrape DOJ Antitrust Division press releases using Selenium."""

import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_press_release_links(driver, page):
    """Get press release links from a listing page."""
    url = f"https://www.justice.gov/atr/press-releases?page={page}"
    driver.get(url)
    time.sleep(3)

    links = []
    for el in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
        href = el.get_attribute("href")
        if href and ("/pr/" in href or "/press-release/" in href):
            if href not in links:
                links.append(href)

    return links


def scrape_press_release(driver, url):
    """Scrape a single press release page."""
    driver.get(url)
    time.sleep(2)

    try:
        title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except Exception:
        title = ""

    try:
        date = driver.find_element(By.CSS_SELECTOR, "time").text.strip()
    except Exception:
        date = ""

    try:
        body = driver.find_element(By.CSS_SELECTOR, ".field--name-body").text.strip()
    except Exception:
        try:
            body = driver.find_element(By.CSS_SELECTOR, "article").text.strip()
        except Exception:
            body = ""

    return {
        "url": url,
        "title": title,
        "date": date,
        "body": body,
    }


def main():
    output_path = Path("datasets/antitrust_v1/raw_press_releases.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    driver = get_driver()

    all_links = []
    for page in range(0, 5):
        print(f"Fetching links from page {page}")
        links = get_press_release_links(driver, page)
        print(f"  Found {len(links)} links")
        all_links.extend(links)

    # Deduplicate
    all_links = list(dict.fromkeys(all_links))
    print(f"\nTotal unique links: {len(all_links)}")

    results = []
    for i, link in enumerate(all_links[:30], start=1):
        print(f"[{i}/{min(30, len(all_links))}] {link}")
        try:
            result = scrape_press_release(driver, link)
            if result["body"]:
                results.append(result)
        except Exception as e:
            print(f"  Error: {e}")

    driver.quit()

    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDone. Saved {len(results)} press releases to {output_path}")


if __name__ == "__main__":
    main()
