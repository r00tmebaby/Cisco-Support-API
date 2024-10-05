from fastapi import APIRouter, Depends

from app.config import logging
from app.utils import PaginationParams, paginate

best_practices_router = APIRouter(
    prefix="/configBestPractices", tags=["Config Best Practices"]
)

logger = logging.getLogger("config_best_practices")


@best_practices_router.get(
    "/summary",
    summary="Get Best Practices",
    description="Retrieve a list of best practices",
)
@paginate
def best_practice(pagination: PaginationParams = Depends()): ...
@best_practices_router.get(
    "/rules",
    summary="Get Best Practices",
    description="Retrieve a list of best practices",
)
@paginate
def best_practice(pagination: PaginationParams = Depends()): ...


@paginate
def best_practice(pagination: PaginationParams = Depends()): ...
@best_practices_router.get(
    "/details",
    summary="Get Best Practices",
    description="Retrieve a list of best practices",
)
@paginate
def best_practice(pagination: PaginationParams = Depends()): ...
