import asyncio
import json
from asyncio import Semaphore
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import logging

# Base URLs
BASE_URL = "https://www.cisco.com/c/en/us/support/"
SEMAPHORE_LIMIT = 10  # To limit the number of concurrent requests
logger = logging.Logger("GetCiscoProductsJob")
semaphore = Semaphore(SEMAPHORE_LIMIT)


async def get_page_soup(client, url):
    """Fetches and parses HTML content from a URL using BeautifulSoup asynchronously."""
    async with semaphore:
        response = await client.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        else:
            logging.error(f"Failed to retrieve content from {url}")
            return None


async def extract_product_links(soup):
    """Extracts product links from the parsed HTML page asynchronously."""
    product_links = []
    section = soup.find("div", {"data-config-metrics-title": "Products by Category"})
    if section:
        links = section.find_all("a")
        for link in links:
            relative_url = link.get("href")
            product_url = urljoin(BASE_URL, relative_url)  # Fix the relative URL issue
            product_links.append({"product": link.text.strip(), "url": product_url})
    return product_links


async def extract_supported_products(client, product_url):
    """Extracts supported product names and links from a product page asynchronously."""
    products = []
    soup = await get_page_soup(client, product_url)
    if soup:
        supported_products_section = soup.find("div", id="allSupportedProducts")
        if supported_products_section:
            product_links = supported_products_section.find_all("a")
            for product_link in product_links:
                product_name = product_link.text.strip()
                product_url = urljoin(
                    BASE_URL, product_link["href"]
                )  # Fix relative URLs here too
                products.append({"name": product_name, "url": product_url})
    return products


async def scrape_cisco_products(file_name: str):
    """Main async method to scrape Cisco product data and save it to a JSON file."""
    async with httpx.AsyncClient() as client:
        soup = await get_page_soup(client, BASE_URL + "index.html")
        if soup:
            product_list = await extract_product_links(soup)
            products_by_category = {}

            tasks = []
            for product in product_list:
                product_name = product["product"]
                product_url = product["url"]
                logger.info(f"Scraping supported products for: {product_name}")
                task = asyncio.create_task(
                    extract_supported_products(client, product_url)
                )
                tasks.append((product_name, task))

            for product_name, task in tasks:
                supported_products = await task
                products_by_category[product_name] = supported_products

            # Save the scraped data to a JSON file
            with open(file_name, "w") as f:
                json.dump(products_by_category, f, indent=4)

            logger.info("JSON file has been created successfully.")
        else:
            logger.error("Failed to load the main Cisco support page.")
