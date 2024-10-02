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
    def extract_products_eol(self, pid: str) -> List[Any]:
        """
        Extract products alerts from the tar file.
        :param pid: Device Product ID
        :return: List of features.
        """
        products = self.extract_raw_file(file_name)

        return []
