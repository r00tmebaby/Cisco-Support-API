import json

from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

field_notices_link = "products-field-notices-list.html"
eos_eos_notices_link = "eos-eol-notice-listing.html"

"https://www.cisco.com/c/en/us/products/switches/catalyst-3560-series-switches/eos-eol-notice-listing.html"

# Initialize the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Navigate to the Cisco support website
driver.get("https://www.cisco.com/c/en/us/support/index.html")

# Optionally, add a wait time to ensure the page loads completely
driver.maximize_window()
driver.implicitly_wait(2)

# Locate the section containing the product type links
section = driver.find_element(
    By.XPATH, '//div[@data-config-metrics-title="Products by Category"]'
)
links = section.find_elements(By.TAG_NAME, "a")
product_list = [
    {"product": i.text, "url": i.get_attribute("href")} for i in links
]
# Initialize a dictionary to hold the products by category
products_by_category = {}

# Iterate over each product type link
for product in product_list:
    driver.get(product["url"])
    # Wait for the "All Supported Products" section to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "allSupportedProducts"))
        )
    except TimeoutException:
        continue
    # Initialize a list to hold the products
    products = []

    # Find all product links in the "All Supported Products" section
    all_supported_products = driver.find_element(By.ID, "allSupportedProducts")

    product_links = all_supported_products.find_elements(By.TAG_NAME, "a")

    # Extract the product names and URLs
    for product_link in product_links:
        product_name = product_link.text

        product_url = product_link.get_attribute("href")

        products.append({"name": product_name, "url": product_url})
    products_by_category[product["product"]] = products

# Close the WebDriver
driver.quit()

# Save the products by category to a JSON file
with open("products_by_category.json", "w") as f:
    json.dump(products_by_category, f, indent=4)

print("JSON file has been created successfully.")
