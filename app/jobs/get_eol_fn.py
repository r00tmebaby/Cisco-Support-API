from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from threading import Semaphore
from typing import Dict, List, Union
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import GetEOLConfig, logging
from app.jobs.get_cisco_products import scrape_cisco_products
from app.utils import (
    normalize_date_format,
    normalize_to_camel_case,
    save_to_json,
)


class CiscoEOLJob:
    """
    The CiscoEOLJob class is responsible for extracting and processing Cisco EOL (End of Life), EOS (End of Sale),
    and FN (Field Notice) data. It uses scraping techniques to retrieve this data from Cisco's support website and
    outputs it in a structured format.

    The following data is extracted:
    - EOL/EOS Notices: Extracts milestone dates, affected products, and other relevant details from Cisco's EOL/EOS notices.
    - Field Notices (FN): Extracts detailed information about Cisco product field notices, including problem symptoms,
      revisions, affected products, and workarounds.

    This class supports both asynchronous HTTP requests and HTML parsing using BeautifulSoup to scrape and process the data.
    The extracted data is then saved to local JSON files for further use.
    """

    logger = logging.getLogger("CiscoEOLJob")
    config = GetEOLConfig()
    Path(config.EOL_FOLDER).mkdir(parents=True, exist_ok=True)

    def __init__(self):
        """
        Initialize the CiscoEOLJob class, set up logging, and create necessary directories for storing data.

        This constructor ensures that the environment is correctly set up, including Windows-specific event loop handling.
        """

        # Workaround for Windows event loop issue
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    @classmethod
    async def _process_eol_page(
        cls, client: httpx.AsyncClient, eol_url: str
    ) -> Union[Dict[str, str], None]:
        """
        Fetch and process the EOL (End of Life) page to extract relevant data like EOL ID, description, dates, and affected products.

        :param client: The HTTP client used for making asynchronous requests.
        :param eol_url: The URL of the EOL page to be processed.
        :return: A dictionary of extracted EOL data or None if processing fails.
        """
        try:
            response = await client.get(eol_url, follow_redirects=True, timeout=None)
            await asyncio.sleep(cls.config.TIMEOUT_THREAD)

            if response.status_code in [200, 403]:
                cls.logger.info(f"Processing EOL response from: {eol_url}")
                eol_soup = BeautifulSoup(response.text, "html.parser")

                # Extract key information using helper methods
                eol_id = cls._extract_eol_id(eol_soup)
                description = cls._extract_description(eol_soup)
                dates = cls._extract_milestone_dates(eol_soup)
                product_part_numbers = cls._extract_product_part_numbers(eol_soup)

                if eol_id is not None:
                    eol_id.replace(" - Amended", "")

                cls.logger.info(f"Processing EOL successful: {eol_url}")
                return {
                    "bulletinId": eol_id,
                    "url": eol_url,
                    "description": description,
                    "dates": dates,
                    "affectedProducts": product_part_numbers,
                }
            else:
                cls.logger.error(
                    f"Error fetching EOL notice from {eol_url}: {response.status_code}"
                )
                return None
        except Exception as e:
            cls.logger.error(f"Error processing EOL page {eol_url}: {str(e)}")
            return None

    @classmethod
    def _extract_eol_id(cls, eol_soup: BeautifulSoup) -> Union[str, None]:
        """
        Extract the EOL ID (Bulletin ID) from the EOL page.

        :param eol_soup: Parsed HTML of the EOL page.
        :return: The EOL ID as a string or None if not found.
        """
        eol_id_element = eol_soup.select_one("p.pSubhead2CMT")
        if not eol_id_element:
            eol_id_element = eol_soup.select_one("p.pToC_Subhead2")
        return eol_id_element.get_text(strip=True) if eol_id_element else None

    @classmethod
    def _extract_description(cls, eol_soup: BeautifulSoup) -> Union[str, None]:
        """
        Extract the description from the EOL page.

        :param eol_soup: Parsed HTML of the EOL page.
        :return: The description of the EOL notice or None if not found.
        """
        description_element = eol_soup.select_one("p.pIntroCMT")
        return description_element.get_text(strip=True) if description_element else None

    @staticmethod
    def _extract_milestone_dates(eol_soup: BeautifulSoup) -> list:
        """
        Extract the milestone dates such as End-of-Life Announcement, End-of-Sale Date, and others from the EOL page.

        :param eol_soup: Parsed HTML of the EOL page.
        :return: A list of dictionaries containing milestone dates and their relevant details.
        """
        dates = []
        milestones_table = eol_soup.find("table")

        if milestones_table:
            rows = milestones_table.find_all("tr")
            date_obj = {}

            for row in rows:
                columns = row.find_all("td")
                if len(columns) >= 3:
                    milestone_name = columns[0].get_text(strip=True)
                    affected = milestone_name.split(":")
                    affected = affected[1] if len(affected) == 2 else "N/A"
                    raw_date = columns[2].get_text(strip=True)
                    formatted_date = normalize_date_format(raw_date, "%B %d, %Y")

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
                            date_obj[key] = {
                                "affects": affected,
                                "date": formatted_date,
                            }
                            break

            dates.append(date_obj)
        return dates

    @staticmethod
    def _extract_product_part_numbers(eol_soup: BeautifulSoup) -> list:
        """
        Extract the affected product part numbers from the EOL page.

        :param eol_soup: Parsed HTML of the EOL page.
        :return: A list of affected product part numbers.
        """
        product_part_numbers = []
        affected_products_table = (
            eol_soup.find_all("table")[1]
            if len(eol_soup.find_all("table")) > 1
            else None
        )

        if affected_products_table:
            product_rows = affected_products_table.find_all("tr")
            for product_row in product_rows[1:]:
                columns = product_row.find_all("td")
                if len(columns) > 0:
                    part_number = columns[0].get_text(strip=True)
                    product_part_numbers.append(part_number)

        return product_part_numbers

    @classmethod
    async def _process_fn_page(cls, client, fn_url: str) -> Union[Dict[str, str], None]:
        """
        Fetch and process the Field Notice (FN) page to extract key data such as notice ID, description, and affected products.

        :param client: The HTTP client used for making asynchronous requests.
        :param fn_url: The URL of the FN page to be processed.
        :return: A dictionary of extracted FN data or None if processing fails.
        """
        try:
            response = await client.get(fn_url, follow_redirects=True, timeout=None)
            await asyncio.sleep(cls.config.TIMEOUT_THREAD)

            if response.status_code in [200, 403]:
                cls.logger.info(f"Processing FN response from: {fn_url}")
                fn_soup = BeautifulSoup(response.text, "html.parser")

                fn_title = fn_soup.select_one("#fw-pagetitle").get_text(strip=True)

                background_info = cls._extract_background_info(fn_soup)
                problem_description_info = cls._extract_problem_description(fn_soup)
                products = cls._extract_affected_products(fn_soup)
                problem_symptom_info = cls._extract_problem_symptoms(fn_soup)
                revisions = cls._extract_revisions(fn_soup)
                updated_date_standardized = cls._extract_updated_date(fn_soup)
                workaround, description_short = cls.extract_workaround(fn_title)

                cls.logger.info(f"Processing FN successful: {fn_url}")
                return {
                    "noticeID": re.search(r"\d+", fn_title).group()
                    or fn_soup.select_one("documentId").get_text(strip=True),
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
            cls.logger.error(
                f"Processing FN unsuccessful: {fn_url} with error: {str(e)}"
            )
            return None

    @classmethod
    def _extract_background_info(cls, soup: BeautifulSoup) -> str:
        """
        Extract the background information from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: The background information as a string.
        """
        try:
            background = soup.find("h3", string="Background")
            if background:
                return background.find_next("p").get_text(strip=True)
        except Exception as e:
            cls.logger.warning(f"Error parsing background info: {str(e)}")
        return ""

    @classmethod
    def _extract_problem_description(cls, soup: BeautifulSoup) -> str:
        """
        Extract the problem description from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: The problem description as a string.
        """
        try:
            problem_description = soup.find("h3", string="Problem Description")
            if problem_description:
                paragraphs = problem_description.find_next_siblings("p")
                return "\n".join([p.get_text(strip=True) for p in paragraphs])
        except Exception as e:
            cls.logger.error(f"Error parsing problem description: {str(e)}")
        return ""

    @classmethod
    def _extract_affected_products(cls, soup: BeautifulSoup) -> list:
        """
        Extract the affected products from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: A list of dictionaries containing affected product information.
        """
        products = []
        try:
            products_affected = soup.find("h3", string="Products Affected")
            if products_affected:
                product_tables = products_affected.find_all_next("table", limit=2)
                product_table = None
                for table in product_tables:
                    rows = table.find_all("tr")
                    if len(rows) >= 1:
                        product_table = table
                        break

                if product_table:
                    headers = [
                        normalize_to_camel_case(th.get_text(strip=True))
                        for th in product_table.find_all("th")
                    ]
                    for row in product_table.find_all("tr")[1:]:
                        columns = row.find_all("td")
                        product_data = {}
                        for idx, column in enumerate(columns):
                            if idx < len(headers):
                                product_data[headers[idx]] = column.get_text(strip=True)
                        products.append(product_data)
        except Exception as e:
            cls.logger.warning(f"Error parsing affected products: {str(e)}")
        return products

    @classmethod
    def _extract_problem_symptoms(cls, soup: BeautifulSoup) -> str:
        """
        Extract the problem symptoms from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: The problem symptoms as a string.
        """
        try:
            problem_symptom = soup.find("h3", string="Problem Symptom")
            if problem_symptom:
                paragraphs = problem_symptom.find_next_siblings("p")
                return "\n".join([p.get_text(strip=True) for p in paragraphs])
        except Exception as e:
            cls.logger.warning(f"Error parsing problem symptoms: {str(e)}")
        return ""

    @classmethod
    def _extract_revisions(cls, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract the revision history from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: A list of dictionaries containing revision data.
        """
        revisions = []
        try:
            revisions_table = soup.find("table", {"border": "1"})
            if revisions_table:
                row_revisions = revisions_table.find_all("tr")
                if len(row_revisions) > 1:
                    rows = revisions_table.find_all("tr")[1:]  # Skip the header row
                    for row in rows:
                        columns = row.find_all("td")
                        try:
                            revision_data = {
                                "revision": columns[0].get_text(strip=True),
                                "publish_date": columns[1].get_text(strip=True),
                                "comments": columns[2].get_text(strip=True),
                            }
                            revisions.append(revision_data)
                        except Exception as e:
                            cls.logger.warning(
                                f"Error parsing revision history data first attempt, error: {str(e)}"
                            )
                            try:
                                revisions_text = soup.find(
                                    "h3", string="Revision History"
                                )
                                revision_table = revisions_text.find_next(
                                    "table", {"border": "1"}
                                )
                                row_revisions = revision_table.find_all("tr")
                                if len(row_revisions) > 1:
                                    headers = [
                                        normalize_to_camel_case(tr.get_text(strip=True))
                                        for tr in row_revisions[0].find_all("td")
                                    ]
                                    for rows in row_revisions[1:]:
                                        columns = rows.find_all("td")
                                        revisions_data = {}

                                        # Populate the product_data dictionary dynamically based on headers
                                        for idx, column in enumerate(columns):
                                            if idx < len(headers):
                                                revisions_data[headers[idx]] = (
                                                    column.get_text(strip=True)
                                                )
                                        revisions.append(revisions_data)
                            except Exception as e:
                                cls.logger.warning(
                                    f"Error parsing revision history data second attempt, error: {str(e)}"
                                )
        except Exception as e:
            cls.logger.warning(f"Error revisions can not be parsed: {e}")
            return []

    @classmethod
    def _extract_updated_date(cls, soup: BeautifulSoup) -> str:
        """
        Extract the last updated date from the Field Notice (FN) page.

        :param soup: Parsed HTML of the FN page.
        :return: The last updated date in 'DD-MM-YYYY' format.
        """
        try:
            updated_date_raw = (
                soup.select_one(".updatedDate").text
                if soup.select_one(".updatedDate")
                else ""
            )
            if updated_date_raw:
                date_match = re.search(
                    r"Updated:(\w+ \d{1,2}, \d{4})", updated_date_raw
                )
                if date_match:
                    extracted_date = date_match.group(1)
                    date_obj = datetime.strptime(extracted_date, "%B %d, %Y")
                    return date_obj.strftime("%d-%m-%Y")
        except Exception as e:
            cls.logger.warning(f"Error parsing updated date: {e}")
        return ""

    @classmethod
    def extract_workaround(cls, fn_title: str) -> tuple:
        """
        Extract the workaround status and short description from the FN title.

        :param fn_title: The Field Notice title string.
        :return: A tuple containing the workaround status (boolean) and the short description.
        """
        try:
            title_parts = fn_title.split(" - ")
            if len(title_parts) == 4:
                workaround = title_parts[3] == "Workaround Provided"
                description_short = title_parts[2]
                return workaround, description_short
        except Exception as e:
            cls.logger.warning(f"Error parsing workaround: {e}")
        return "", ""

    @classmethod
    async def support_page_parser(
        cls,
        page: str,
        client: httpx.AsyncClient,
        path: str,
        semaphore: Semaphore,
    ):
        """
        Parse the support page to extract both EOL (End of Life) and FN (Field Notice) data and save it to JSON files.

        :param page: The URL of the support page.
        :param client: The HTTP client used for making asynchronous requests.
        :param path: The file path where the extracted data should be saved.
        :param semaphore: Semaphore object for limiting concurrent requests.
        """
        async with semaphore:
            try:
                await asyncio.sleep(cls.config.TIMEOUT_REQUESTS)
                eos_object = {}
                response = await client.get(page, follow_redirects=True, timeout=None)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                rows = soup.select("table tr")
                for row in rows:
                    label_element = row.find("th")
                    value_element = row.find("td")
                    if label_element and value_element:
                        label_text = label_element.get_text(strip=True)
                        value_text = value_element.get_text(strip=True)
                        if "Series Release Date" in label_text:
                            eos_object["SeriesReleaseDate"] = normalize_date_format(
                                value_text
                            )
                        elif "End-of-Sale Date" in label_text:
                            eos_object["EndOfSaleDate"] = normalize_date_format(
                                value_text
                            )
                        elif "End-of-Support Date" in label_text:
                            eos_object["EndOfSupportDate"] = normalize_date_format(
                                value_text
                            )
                cls.logger.info(f"Extracted EoS/EoL information from {page}")

                eos_object["EOLS"] = []
                get_eol_url = page.replace("/support/", "/products/").replace(
                    "series.html", cls.config.EOS_EOS_NOTICES_LINK
                )

                response = await client.get(get_eol_url, timeout=None)
                await asyncio.sleep(cls.config.TIMEOUT_REQUESTS)

                if response.status_code in [200, 403]:
                    soup = BeautifulSoup(response.text, "html.parser")
                    all_links = soup.find_all("a", href=True)
                    for link in all_links:
                        href = link["href"]
                        if "eol.html" in href:
                            eol_url = urljoin("https://www.cisco.com", href)
                            cls.logger.info(f"Processing EOL URL: {eol_url}")
                            eol_data = await cls._process_eol_page(client, eol_url)
                            if eol_data:
                                eos_object["EOLS"].append(eol_data)
                else:
                    cls.logger.error(
                        f"Error fetching EOL notices from {get_eol_url}: {response.status_code}"
                    )

                eos_object["FNS"] = []
                get_notices_url = page.replace(
                    "series.html", cls.config.FIELD_NOTICES_LINK
                )
                response = await client.get(get_notices_url, timeout=None)
                await asyncio.sleep(cls.config.TIMEOUT_REQUESTS)

                if response.status_code in [200, 403]:
                    soup = BeautifulSoup(response.text, "html.parser")
                    all_links = set(soup.find_all("a", href=True))
                    for link in all_links:
                        href = link["href"]
                        if "field-notices" in href:
                            get_notices_url = urljoin("https://www.cisco.com", href)
                            cls.logger.info(f"Processing FN URL: {get_notices_url}")
                            fn_data = await cls._process_fn_page(
                                client, get_notices_url
                            )
                            if fn_data:
                                eos_object["FNS"].append(fn_data)
                else:
                    cls.logger.error(
                        f"Error fetching FN from {get_notices_url}: {response.status_code}"
                    )

                await save_to_json(eos_object, GetEOLConfig.EOL_FILE_NAME)
            except Exception as e:
                cls.logger.error(f"Error processing support page {page}: {str(e)}")

            cls.logger.info(f"Finished parsing {page}")
            return eos_object

    async def fetch_data(self) -> None:
        """Main function to run the Cisco EOL/EOS/FN parser and create a tar.gz archive after processing."""

        try:
            with open(self.config.CATEGORIES_JSON_PATH) as file:
                products_by_category = json.load(file)
        except:
            self.logger.warning("Products JSON file not found, will try to create one")
            try:
                await scrape_cisco_products(self.config.CATEGORIES_JSON_PATH)
                with open(self.config.CATEGORIES_JSON_PATH) as file:
                    products_by_category = json.load(file)
            except SystemError:
                raise (
                    FileNotFoundError(
                        f"Could not create {self.config.CATEGORIES_JSON_PATH}"
                    )
                )

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True
        ) as client:
            semaphore = asyncio.Semaphore(self.config.CONCURRENT_REQUESTS)
            tasks = []

            for device_category in products_by_category.keys():
                for product in products_by_category.get(device_category):
                    product_family, product_url = product.values()
                    path = os.path.join(
                        self.config.EOL_FOLDER, device_category, product_family
                    )
                    self.logger.info(f"Processing product family: {product_family}")
                    tasks.append(
                        self.support_page_parser(
                            product_url, client, str(path), semaphore
                        )
                    )

            # Wait for all the tasks to complete
            await asyncio.gather(*tasks)

        # Create tar.gz archive of the EOL_FOLDER
        tar_filename = os.path.join(self.config.BASE_FOLDER, self.config.ARCHIVE_FILE)

        with tarfile.open(
            tar_filename, "w:gz", compresslevel=self.config.COMPRESSION_LEVEL
        ) as tar:
            tar.add(
                self.config.EOL_FOLDER,
                arcname=os.path.basename(self.config.EOL_FOLDER),
            )

        self.logger.info(f"Data archived to {tar_filename}")
        try:
            # Delete the EOL_FOLDER and its contents after archiving
            shutil.rmtree(self.config.EOL_FOLDER)
            self.logger.info(f"Deleted the folder: {self.config.EOL_FOLDER}")
            self.logger.info("Job has finished successfully!")
        except (FileNotFoundError, IOError):
            self.logger.error(f"Folder {self.config.EOL_FOLDER} could not be deleted")
            self.logger.warning("Job has not finished successfully!")
