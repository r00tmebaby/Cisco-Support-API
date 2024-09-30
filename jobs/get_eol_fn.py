from __future__ import annotations

import re
import sys
import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from job_orig import logger


class CiscoParser:
    """Class to handle the extraction of Cisco EOL, EOS, and FN data."""

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # Get the project root directory
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

    FIELD_NOTICES_LINK = "products-field-notices-list.html"
    EOS_EOS_NOTICES_LINK = "eos-eol-notice-listing.html"
    CISCO_SUPPORT_URL = "https://www.cisco.com/c/en/us/support/index.html"
    CONCURRENT_REQUESTS = 10
    TIMEOUT_THREAD = 1
    TIMEOUT_REQUESTS = 1

    BASE_FOLDER = os.path.join(PROJECT_ROOT, "data")
    EOL_FOLDER = os.path.join(BASE_FOLDER, "eol-eos")
    CATEGORIES_JSON_PATH = os.path.join(BASE_FOLDER, "products_by_category.json")

    def __init__(self):
        """Initialize logger and configure environment-specific settings."""
        self._setup_logging()

        Path(self.EOL_FOLDER).mkdir(parents=True, exist_ok=True)

        # Workaround for Windows event loop issue
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def _setup_logging(self):
        """Set up the logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def convert_date_format(date_str: str) -> str:
        """Converts date format from 'dd-MMM-yyyy' to 'dd-mm-yyyy'."""
        try:
            date_object = datetime.strptime(date_str, '%d-%b-%Y')
            return date_object.strftime('%d-%m-%Y')
        except ValueError:
            logging.error(f"Failed to convert date format for {date_str}")
            return date_str

    @staticmethod
    def convert_eol_dates(date_str: str) -> str:
        """Converts date from 'Month Day, Year' to 'DD-MM-YYYY'."""
        try:
            parsed_date = datetime.strptime(date_str, "%B %d, %Y")
            return parsed_date.strftime("%d-%m-%Y")
        except ValueError:
            logging.error(f"Failed to parse EOL date: {date_str}")
            return date_str

    async def process_eol_page(self, client: httpx.AsyncClient, eol_url: str) -> Union[Dict[str, str], None]:
        """Processes an EOL page and extracts key data."""
        try:
            response = await client.get(eol_url, follow_redirects=True, timeout=None)
            await asyncio.sleep(self.TIMEOUT_THREAD)

            if response.status_code in [200, 403]:
                logging.info(f"Processing EOL response from: {eol_url}")
                eol_soup = BeautifulSoup(response.text, 'html.parser')

                # Extract key information using helper methods
                eol_id = self._extract_eol_id(eol_soup)
                description = self._extract_description(eol_soup)
                dates = self._extract_milestone_dates(eol_soup)
                product_part_numbers = self._extract_product_part_numbers(eol_soup)

                if eol_id is not None:
                    eol_id.replace(" - Amended", "")

                logging.info(f"Processing EOL successful: {eol_url}")
                return {
                    "bulletinId": eol_id,
                    "url": eol_url,
                    "description": description,
                    "dates": dates,
                    "affectedProducts": product_part_numbers
                }
            else:
                logging.error(f"Error fetching EOL notice from {eol_url}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error processing EOL page {eol_url}: {str(e)}")
            return None

    @classmethod
    def _extract_eol_id(cls, eol_soup: BeautifulSoup) -> Union[str, None]:
        """Extracts the EOL ID (Bulletin ID) from the EOL page."""
        eol_id_element = eol_soup.select_one('p.pSubhead2CMT')
        return eol_id_element.get_text(strip=True) if eol_id_element else None

    @classmethod
    def _extract_description(cls, eol_soup: BeautifulSoup) -> Union[str, None]:
        """Extracts the description from the EOL page."""
        description_element = eol_soup.select_one('p.pIntroCMT')
        return description_element.get_text(strip=True) if description_element else None

    def _extract_milestone_dates(self, eol_soup: BeautifulSoup) -> list:
        """Extracts milestone dates from the EOL page."""
        dates = []
        milestones_table = eol_soup.find('table')

        if milestones_table:
            rows = milestones_table.find_all('tr')
            date_obj = {}

            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 3:
                    milestone_name = columns[0].get_text(strip=True)
                    affected = milestone_name.split(":")
                    affected = affected[1] if len(affected) == 2 else "N/A"
                    raw_date = columns[2].get_text(strip=True)
                    formatted_date = self.convert_eol_dates(raw_date)

                    milestone_mapping = {
                        "End-of-Life Announcement": "endOfLifeAnnouncementDate",
                        "End-of-Sale": "endOfSaleDate",
                        "Last Ship": "lastShipDate",
                        "End of SW Maintenance": "endOfSoftwareMaintenance",
                        "End of Vulnerability/Security": "endOfVulnerabilitySecuritySupport",
                        "End of New Service": "endOfNewServiceAttachmentDate",
                        "Last Date of Support": "lastDateOfSupport",
                        "End of Service Contract Renewal": "endOfServiceContractRenewalDate",
                        "End of Routine Failure Analysis": "endOfRoutineFailureAnalysisDate",
                    }

                    for keyword, key in milestone_mapping.items():
                        if keyword in milestone_name:
                            date_obj[key] = {"affects": affected, "date": formatted_date}
                            break

            dates.append(date_obj)
        return dates

    @classmethod
    def _extract_product_part_numbers(cls, eol_soup: BeautifulSoup) -> list:
        """Extracts the affected product part numbers from the EOL page."""
        product_part_numbers = []
        affected_products_table = eol_soup.find_all('table')[1] if len(eol_soup.find_all('table')) > 1 else None

        if affected_products_table:
            product_rows = affected_products_table.find_all('tr')
            for product_row in product_rows[1:]:
                columns = product_row.find_all('td')
                if len(columns) > 0:
                    part_number = columns[0].get_text(strip=True)
                    product_part_numbers.append(part_number)

        return product_part_numbers

    @staticmethod
    def normalize_to_camel_case(header: str) -> str:
        """Normalizes a table header to camelCase."""
        words = re.sub(r'[^\w\s]', '', header).split()  # Remove special characters and split by spaces
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

    async def process_fn_page(self, client, fn_url: str) -> Union[Dict[str, str], None]:
        """Processes a Field Notice (FN) page and extracts key data."""
        try:
            response = await client.get(fn_url, follow_redirects=True, timeout=None)
            await asyncio.sleep(self.TIMEOUT_THREAD)

            if response.status_code in [200, 403]:
                logging.info(f"Processing FN response from: {fn_url}")
                fn_soup = BeautifulSoup(response.text, 'html.parser')

                fn_title = fn_soup.select_one('#fw-pagetitle').get_text(strip=True)

                background_info = self._extract_background_info(fn_soup)
                problem_description_info = self._extract_problem_description(fn_soup)
                products = self._extract_affected_products(fn_soup)
                problem_symptom_info = self._extract_problem_symptoms(fn_soup)
                revisions = self._extract_revisions(fn_soup)
                updated_date_standardized = self._extract_updated_date(fn_soup)
                workaround, description_short = self.extract_workaround(fn_title)

                logging.info(f"Processing FN successful: {fn_url}")
                return {
                    "noticeID": re.search(r"\d+", fn_title).group() or fn_soup.select_one('documentId').get_text(strip=True),
                    "url": fn_url,
                    "updatedDate": updated_date_standardized,
                    "descriptionShort": description_short,
                    "descriptionLong": problem_description_info,
                    "background": background_info,
                    "problemSymptom": problem_symptom_info,
                    "workaround": workaround,
                    "revisions": revisions,
                    "productsAffected": products,
                }
        except Exception as e:
            logging.error(f"Processing FN unsuccessful: {fn_url} with error: {str(e)}")
            return None

    @classmethod
    def _extract_background_info(cls, soup: BeautifulSoup) -> str:
        """Extracts background info from the FN page."""
        try:
            background = soup.find('h3', string='Background')
            if background:
                return background.find_next('p').get_text(strip=True)
        except Exception as e:
            logging.warning(f"Error parsing background info: {str(e)}")
        return ""

    @classmethod
    def _extract_problem_description(cls, soup: BeautifulSoup) -> str:
        """Extracts the problem description from the FN page."""
        try:
            problem_description = soup.find('h3', string='Problem Description')
            if problem_description:
                paragraphs = problem_description.find_next_siblings('p')
                return "\n".join([p.get_text(strip=True) for p in paragraphs])
        except Exception as e:
            logging.error(f"Error parsing problem description: {str(e)}")
        return ""

    @classmethod
    def _extract_affected_products(cls, soup: BeautifulSoup) -> list:
        """Extracts affected products from the FN page."""
        products = []
        try:
            products_affected = soup.find('h3', string='Products Affected')
            if products_affected:
                product_tables = products_affected.find_all_next('table', limit=2)
                product_table = None
                for table in product_tables:
                    rows = table.find_all('tr')
                    if len(rows) >= 1:
                        product_table = table
                        break

                if product_table:
                    headers = [cls.normalize_to_camel_case(th.get_text(strip=True)) for th in product_table.find_all('th')]
                    for row in product_table.find_all('tr')[1:]:
                        columns = row.find_all('td')
                        product_data = {}
                        for idx, column in enumerate(columns):
                            if idx < len(headers):
                                product_data[headers[idx]] = column.get_text(strip=True)
                        products.append(product_data)
        except Exception as e:
            logging.warning(f"Error parsing affected products: {str(e)}")
        return products

    @classmethod
    def _extract_problem_symptoms(cls, soup: BeautifulSoup) -> str:
        """Extracts problem symptoms from the FN page."""
        try:
            problem_symptom = soup.find('h3', string='Problem Symptom')
            if problem_symptom:
                paragraphs = problem_symptom.find_next_siblings('p')
                return "\n".join([p.get_text(strip=True) for p in paragraphs])
        except Exception as e:
            logging.warning(f"Error parsing problem symptoms: {str(e)}")
        return ""

    @classmethod
    def _extract_revisions(cls, soup: BeautifulSoup) -> List[Dict[str,str]]:
        """Extracts revisions from the FN page."""
        revisions = []
        try:
            revisions_table = soup.find('table', {'border': '1'})
            if revisions_table:
                row_revisions = revisions_table.find_all('tr')
                if len(row_revisions) > 1:
                    rows = revisions_table.find_all('tr')[1:]  # Skip the header row
                    for row in rows:
                        columns = row.find_all('td')
                        try:
                            revision_data = {
                                "revision": columns[0].get_text(strip=True),
                                "publish_date": columns[1].get_text(strip=True),
                                "comments": columns[2].get_text(strip=True)
                            }
                            revisions.append(revision_data)
                        except Exception as e:
                            logging.warning(f"Error parsing revision history data first attempt, error: {str(e)}")
                            try:
                                revisions_text = soup.find('h3', string='Revision History')
                                revision_table = revisions_text.find_next("table", {'border': '1'})
                                row_revisions = revision_table.find_all('tr')
                                if len(row_revisions) > 1:
                                    headers = [
                                        cls.normalize_to_camel_case(
                                            tr.get_text(strip=True)
                                        ) for tr in row_revisions[0].find_all('td')
                                    ]
                                    for rows in row_revisions[1:]:
                                        columns = rows.find_all('td')
                                        revisions_data = {}

                                        # Populate the product_data dictionary dynamically based on headers
                                        for idx, column in enumerate(columns):
                                            if idx < len(headers):
                                                revisions_data[headers[idx]] = column.get_text(strip=True)
                                        revisions.append(revisions_data)
                            except Exception as e:
                                logging.warning(f"Error parsing revision history data second attempt, error: {str(e)}")
        except Exception as e:
            logging.warning(f"Error revisions can not be parsed: {e}")
            return []

    @classmethod
    def _extract_updated_date(cls, soup:BeautifulSoup) -> str:
        """Extracts the updated date from the FN page."""
        try:
            updated_date_raw = soup.select_one('.updatedDate').text if soup.select_one('.updatedDate') else ''
            if updated_date_raw:
                date_match = re.search(r'Updated:(\w+ \d{1,2}, \d{4})', updated_date_raw)
                if date_match:
                    extracted_date = date_match.group(1)
                    date_obj = datetime.strptime(extracted_date, '%B %d, %Y')
                    return date_obj.strftime('%d-%m-%Y')
        except Exception as e:
            logging.warning(f"Error parsing updated date: {e}")
        return ""

    @classmethod
    def extract_workaround(cls, fn_title: str) -> tuple:
        """Extracts the workaround status and short description from the FN title."""
        try:
            title_parts = fn_title.split(" - ")
            if len(title_parts) == 4:
                workaround = title_parts[3] == "Workaround Provided"
                description_short = title_parts[2]
                return workaround, description_short
        except Exception as e:
            logging.warning(f"Error parsing workaround: {e}")
        return "", ""


    async def support_page_parser(self, page: str, client: httpx.AsyncClient, path: str, semaphore):
        """Parses the support page to extract EOL and FN data."""
        async with semaphore:
            try:
                await asyncio.sleep(self.TIMEOUT_REQUESTS)
                eos_object = {}
                response = await client.get(page, follow_redirects=True, timeout=None)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                rows = soup.select("table tr")
                for row in rows:
                    label_element = row.find("th")
                    value_element = row.find("td")
                    if label_element and value_element:
                        label_text = label_element.get_text(strip=True)
                        value_text = value_element.get_text(strip=True)
                        if "Series Release Date" in label_text:
                            eos_object["SeriesReleaseDate"] = self.convert_date_format(value_text)
                        elif "End-of-Sale Date" in label_text:
                            eos_object["EndOfSaleDate"] = self.convert_date_format(value_text)
                        elif "End-of-Support Date" in label_text:
                            eos_object["EndOfSupportDate"] = self.convert_date_format(value_text)
                logging.info(f"Extracted EoS/EoL information from {page}")

                eos_object["EOLS"] = []
                get_eol_url = page.replace("/support/", "/products/").replace("series.html", self.EOS_EOS_NOTICES_LINK)

                response = await client.get(get_eol_url, timeout=None)
                await asyncio.sleep(self.TIMEOUT_REQUESTS)

                if response.status_code in [200, 403]:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link['href']
                        if 'eol.html' in href:
                            eol_url = urljoin('https://www.cisco.com', href)
                            logging.info(f"Processing EOL URL: {eol_url}")
                            eol_data = await self.process_eol_page(client, eol_url)
                            if eol_data:
                                eos_object["EOLS"].append(eol_data)
                else:
                    logging.error(f"Error fetching EOL notices from {get_eol_url}: {response.status_code}")

                eos_object["FNS"] = []
                get_notices_url = page.replace("series.html", self.FIELD_NOTICES_LINK)
                response = await client.get(get_notices_url, timeout=None)
                await asyncio.sleep(self.TIMEOUT_REQUESTS)

                if response.status_code in [200, 403]:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    all_links = set(soup.find_all('a', href=True))
                    for link in all_links:
                        href = link['href']
                        if 'field-notices' in href:
                            get_notices_url = urljoin('https://www.cisco.com', href)
                            logging.info(f"Processing FN URL: {get_notices_url}")
                            fn_data = await self.process_fn_page(client, get_notices_url)
                            if fn_data:
                                eos_object["FNS"].append(fn_data)
                else:
                    logging.error(f"Error fetching FN from {get_notices_url}: {response.status_code}")

                self.save_to_json(eos_object, os.path.join(path, "eol.json"))
            except Exception as e:
                logging.error(f"Error processing support page {page}: {str(e)}")

            logging.info(f"Finished parsing {page}")
            return eos_object

    @staticmethod
    def save_to_json(data: Dict, filename: str) -> None:
        """Saves data to a JSON file."""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
            logging.info(f"Data saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving JSON file {filename}: {str(e)}")


async def main() -> None:
    """Main function to run the Cisco EOL/EOS/FN parser."""
    parser = CiscoParser()
    async with httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0'}, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(parser.CONCURRENT_REQUESTS)
        tasks = []
        with open(CiscoParser.CATEGORIES_JSON_PATH) as file:
            products_by_category = json.load(file)
        for device_category in products_by_category.keys():
            for product in products_by_category.get(device_category):
                product_family, product_url = product.values()
                path = os.path.join(CiscoParser.EOL_FOLDER, device_category, product_family)
                logging.info(f"Processing product family: {product_family}")
                tasks.append(parser.support_page_parser(product_url, client, path, semaphore))
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
