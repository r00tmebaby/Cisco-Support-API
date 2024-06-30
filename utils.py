import inspect
import json
import tarfile
from functools import lru_cache, wraps
from typing import Callable, Union, Any, Dict, List

from fastapi import Query, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.logger import logger
from starlette.responses import JSONResponse


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="The page number for pagination"),
        limit: int = Query(
            20, ge=1, le=1000, description="Limit the number of results per page"
        ),
    ):
        self.page = page
        self.limit = limit

    @property
    def offset(self):
        return (self.page - 1) * self.limit


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
            print(f"Error generating JSON response: {e}")
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
