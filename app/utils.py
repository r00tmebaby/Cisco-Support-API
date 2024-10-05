import inspect
import json
import logging
import os
import re
import tarfile
from datetime import datetime
from functools import lru_cache, wraps
from http.client import responses
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import aiofiles
from click import Tuple
from config import GetFeaturesConfig
from fastapi import Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from app.config import GetEOLConfig

logger = logging.getLogger("Utils")


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="The page number for pagination"),
        limit: int = Query(
            20,
            ge=1,
            le=1000,
            description="Limit the number of results per page",
        ),
    ):
        self.page = page
        self.limit = limit

    @property
    def offset(self):
        return (self.page - 1) * self.limit


async def save_to_json(
    data: Union[List[str], Dict[str, Any]], filename: Path, indent: int = 0
):
    """
    Save the given data to a JSON file.
    :param data: The data to save.
    :param filename: The name of the file to save the data in.
    :param indent: The indent level of the JSON file.
    """
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        indent = indent if indent else None

        async with aiofiles.open(filename, "w") as outfile:
            await outfile.write(json.dumps(data, indent=indent))
            logger.info(f"Saved data to {filename}")
    except Exception as e:
        logger.error(f"Error saving JSON file {filename}: {str(e)}")


def normalize_to_camel_case(header: str) -> str:
    """
    Normalize a table header to camelCase format.

    :param header: The header string to be normalized.
    :return: A string in camelCase format.
    """
    # Remove special characters and split by spaces
    words = re.sub(r"[^\w\s]", "", header).split()
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


def normalize_date_format(date_str: str, date_format: str = "%d-%b-%Y") -> str:
    """
    Converts a date string from 'dd-MMM-yyyy' to 'dd-mm-yyyy'.

    Args:
        date_str (str): The date string to convert.
        date_format (str): The date format to use.
    Returns:
        str: The converted date string or the original one if conversion fails.
    """
    try:
        date_object = datetime.strptime(date_str, date_format)
        return date_object.strftime("%d-%m-%Y")
    except ValueError:
        logger.error(f"Failed to convert date format for {date_str}")
        return date_str


def paginate(func: Callable[..., Union[List[Dict[str, Any]], Dict[str, Any]]]):
    """
    Decorator to paginate the results of a function.

    This decorator is used to wrap an endpoint function and provide automatic pagination
    for its list-based response. It expects the wrapped function to return a list, and
    will paginate the results according to the 'limit' and 'offset' parameters provided
    via the PaginationParams dependency.

    The wrapped function can be a coroutine (async function) or a regular function.

    Args:
        func (Callable[..., Union[List[Dict[str, Any]], Dict[str, Any]]]):
            The function to be wrapped. It should return a list of results that will be paginated.

    Returns:
        Callable: The wrapped function with pagination applied.

    Paginated Response Structure:
        - has_more: Indicates if there are more pages of results beyond the current page.
        - total_pages: The total number of pages based on the limit.
        - current_page: The current page being served.
        - total_items: The total number of items in the result set.
        - data: The paginated data (subset of the original list).

    Raises:
        HTTPException:
            - If the results are not a list, it raises a 500 HTTP error.
            - If there is an issue generating the JSON response, it raises a 500 HTTP error.

    Example:
        >>> @paginate
        >>> async def get_items():
        >>>     return [{"name": "item1"}, {"name": "item2"}]
    """

    @wraps(func)
    async def async_wrapper(*args, pagination: PaginationParams = Depends(), **kwargs):
        limit = pagination.limit
        offset = pagination.offset

        if inspect.iscoroutinefunction(func):
            results = await func(*args, **kwargs, pagination=pagination)
        else:
            results = func(*args, **kwargs, pagination=pagination)

        if isinstance(results, list):
            total_items = len(results)
            paginated_results = results[offset : offset + limit]
        else:
            raise HTTPException(status_code=500, detail="Results should be a list.")

        total_pages = (total_items + limit - 1) // limit  # Calculate total pages
        current_page = pagination.page
        has_more = offset + limit < total_items

        response_data = {
            "has_more": has_more,
            "total_pages": total_pages,
            "current_page": current_page,
            "total_items": total_items,
            "data": paginated_results,
        }

        try:
            response_json = jsonable_encoder(response_data)
            return JSONResponse(content=response_json)
        except Exception as e:
            logger.error(f"Error generating JSON response: {e}")
            raise HTTPException(
                status_code=500, detail="Error generating JSON response"
            )

    return async_wrapper


class TarExtractor:
    """
    Class responsible for extracting files from the tar file and caching the tar file in memory.
    """

    def __init__(self, tar_path: str):
        self.tar_path = tar_path
        self.tar_file = None

    def load_tar_file(self):
        """Load the tar file into memory if not already loaded."""
        if not self.tar_file:
            self.tar_file = tarfile.open(self.tar_path, "r:gz")
            logger.info(f"Tar file loaded into memory: {self.tar_path}")

    def get_tar_file(self):
        """Return the in-memory tar file, loading it if not already loaded."""
        self.load_tar_file()
        return self.tar_file

    def extract_raw_file(self, file_name: str) -> str:
        """
        Extract a raw file from the tar archive as a string.
        :param file_name: The name of the file to extract.
        :return: The raw file content as a string.
        """
        tar = self.get_tar_file()

        try:
            file = tar.extractfile(file_name)
            if file is None:
                logger.warning(f"File {file_name} not found in the tar archive.")
                return ""

            return file.read().decode("utf-8")
        except Exception as ex:
            logger.error(f"Error extracting file {file_name}: {ex}")
            return ""

    def iterate_tar_file(self, target_file_name: str = "eol.json") -> List[dict]:
        """
        Iterate over the tar file and return the content of target files (e.g., 'eol.json').
        :param target_file_name: The name of the file to search for within the tar archive.
        :return: A list of file contents (assumed to be JSON) as dictionaries.
        """
        self.load_tar_file()
        file_contents = []

        # Iterate through each member in the tar archive
        for member in self.tar_file.getmembers():
            # Check if the member is a regular file and ends with 'eol.json'
            if member.isfile() and member.name.endswith(target_file_name):
                # logger.info(f"Found file: {member.name}")
                file_obj = self.tar_file.extractfile(member)
                if file_obj:
                    try:
                        # Assuming the file content is in JSON format, decode and parse it
                        content = file_obj.read().decode("utf-8")
                        json_content = json.loads(content)
                        file_contents.append(json_content)
                    except json.JSONDecodeError as ex:
                        logger.error(f"Error decoding JSON file {member.name}: {ex}")
                    except Exception as ex:
                        logger.error(f"Error reading file {member.name}: {ex}")

        return file_contents


class FeatureExtractor(TarExtractor):
    @lru_cache(maxsize=128)
    def extract_feature(self, file_name: str) -> List[Any]:
        """
        Extract and process features from the tar file.
        :param file_name: The name of the platform-release JSON file.
        :return: List of processed features.
        """
        platform_content = self.extract_raw_file(file_name)
        unique_content = self.extract_raw_file(
            GetFeaturesConfig.UNIQUE_FEATURES_FILENAME
        )

        if not platform_content or not unique_content:
            return []

        # Process the extracted JSON data specific to features
        try:
            features = json.loads(platform_content)
            unique_features = json.loads(unique_content)

            return [
                unique_features[feature]
                for feature in features
                if feature in unique_features
            ]
        except Exception as ex:
            logger.error(f"Error processing features from {file_name}: {ex}")
            return []


class ProductAlertsExtractor(TarExtractor):
    @lru_cache(maxsize=128)
    def extract_products_eol(self) -> Union[list[Any], str]:
        """
        Extract products alerts from the tar file.
        :param pid: Device Product ID
        :return: List of features.
        """
        file_contents = self.iterate_tar_file(target_file_name="eol.json")

        product_alerts = []
        for content in file_contents:
            # Check if the content is a string, then decode as JSON
            if isinstance(content, str):
                try:
                    alerts = json.loads(content)  # Decode JSON if it's a string
                    product_alerts.extend(alerts)
                except json.JSONDecodeError as ex:
                    logger.error(f"Error decoding JSON content: {ex}")
            elif isinstance(content, dict):
                # If content is already a dict, append it directly
                product_alerts.append(content)
            else:
                logger.error(f"Unexpected content type: {type(content)}")

        return product_alerts
