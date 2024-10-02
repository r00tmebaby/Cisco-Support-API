import inspect
import json
import logging
import os
import re
import tarfile
from datetime import datetime
from functools import lru_cache, wraps
from http.client import responses
from typing import Any, Callable, Dict, List, Union

from click import Tuple
from fastapi import Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from config import GetFeaturesConfig

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


def save_to_json(data: Dict, filename: str) -> None:
    """Saves dict data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Data saved to {filename}")
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


class FeatureExtractor:
    """
    Class responsible for extracting features from the tar file and caching the tar file in memory.
    """

    def __init__(self, tar_path: str):
        self.tar_path = tar_path
        self.tar_file = None

    def load_tar_file(self):
        """Load the tar file into memory."""
        if not self.tar_file:
            self.tar_file = tarfile.open(self.tar_path, "r:gz")
            logger.info(f"Features archive file loaded into memory: {self.tar_path}")

    def get_tar_file(self):
        """Return the in-memory tar file, loading it if not already loaded."""
        if not self.tar_file:
            self.load_tar_file()
        return self.tar_file

    @lru_cache(maxsize=128)
    def extract_feature(self, file_name: str) -> List[Any]:
        """
        Extract features from the in-memory tar file based on the file name and return the unique features list.
        :param file_name: The name of the platform-release JSON file.
        :return: List of features.
        """
        tar = self.get_tar_file()

        try:
            platform_file = tar.extractfile(file_name)
            unique_file = tar.extractfile(GetFeaturesConfig.UNIQUE_FEATURES_FILENAME)

            if platform_file is None or unique_file is None:
                logger.warning(f"File {file_name} or unique features not found.")
                return []

            platform_file_content = platform_file.read().decode("utf-8")
            unique_file_content = unique_file.read().decode("utf-8")

            features = json.loads(platform_file_content)
            unique_features = json.loads(unique_file_content)

            # Build the list of features using the feature hashes from the unique features file
            list_of_features = [
                unique_features[feature]
                for feature in features
                if feature in unique_features
            ]

            return list_of_features
        except KeyError as ex:
            logger.error(f"KeyError: {ex}")
            return []
        except Exception as ex:
            logger.error(f"Error extracting features: {ex}")
            return []
