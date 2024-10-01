import inspect
import json
import os
import re
import tarfile
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, List, Union

from fastapi import Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.logger import logger
from starlette.responses import JSONResponse


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


@lru_cache(maxsize=128)
def extract_feature(tar_path: str, file_name: str) -> List[Dict[str, Any]]:
    with tarfile.open(tar_path, "r:gz") as tar:
        try:
            file = tar.extractfile(file_name)
            if file is None:
                logger.warning(
                    "Feature data not found for the given platform_id and release_id."
                )
                return []

            file_content = file.read().decode("utf-8")
            features = json.loads(file_content)
            if not isinstance(features, list):
                logger.warning("Feature data should be a list.")
                return []
            return features
        except KeyError as ex:
            logger.error(ex)
            return []
