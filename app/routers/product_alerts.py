import os
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends
from fastapi.params import Query

from app.config import Config, GetEOLConfig, logging
from app.utils import PaginationParams, ProductAlertsExtractor, paginate

product_alerts_router = APIRouter(prefix="/productAlerts", tags=["Product Alerts"])

logger = logging.getLogger("product_alerts")

# Create a global instance of ProductAlertsExtractor for accessing tar file
product_alerts = ProductAlertsExtractor(
    tar_path=str(os.path.join(Config.PROJECT_DATA_DIR, GetEOLConfig.ARCHIVE_FILE))
)


def filter_notices_by_criteria(
    notices: List[Dict],
    product_id: Optional[str] = None,
    software_type: Optional[str] = None,
    software_version: Optional[str] = None,
    search_fields=None,
) -> List[Dict]:
    """
    Generalized function to filter product alerts by product ID, software type, and software version.
    :param notices: List of notices to filter.
    :param product_id: Optional product ID to filter notices.
    :param software_type: Optional software type to filter notices.
    :param software_version: Optional software version to filter notices.
    :param search_fields: Fields in which to search for software type and version.
    :return: Filtered list of notices.
    """
    if search_fields is None:
        search_fields = ["description", "descriptionLong"]

    filtered_notices = []
    seen_notice_ids = set()

    for notice in notices:
        notice_id = notice.get("url")  # Unique identifier for the notice
        if notice_id in seen_notice_ids:
            continue

        # Check product ID in affected products
        if product_id:
            for affected in notice.get("productsAffected", []):
                if (
                    product_id in affected.get("productsAffected", "")
                    or product_id in affected.get("affectedProductId", "")
                    or product_id in affected.get("affectedProductName", "")
                ):
                    filtered_notices.append(notice)
                    seen_notice_ids.add(notice_id)
                    break

        # Check software type and version in specified fields
        elif software_type and software_version:
            for field in search_fields:
                description = notice.get(field, "")
                if software_type in description and software_version in description:
                    filtered_notices.append(notice)
                    seen_notice_ids.add(notice_id)
                    break

    return filtered_notices


@product_alerts_router.get(
    "/hardwareFieldNotices",
    summary="Get field notices",
    description="Retrieve field notices",
)
@paginate
def field_notices_by_hardware(
    pagination: PaginationParams = Depends(),
    product_id: Optional[str] = Query(None, description="Filter by product id"),
) -> Union[list[dict[str, str]], list[str]]:
    """Get all field notices, optionally filtered by product id.
    :param pagination: Pagination parameters.
    :param product_id: Optional product id to filter field notices.
    :return: List of field notices.
    """
    all_notices = product_alerts.get_list_of_fns()
    filtered_notices = []
    seen_notice_ids = set()

    if not product_id:
        return all_notices

    for notice in all_notices:
        notice_id = notice.get("url")
        for affected in notice.get("productsAffected", []):
            if (
                product_id in affected.get("productsAffected", "")
                or product_id in affected.get("affectedProductId", "")
                or product_id in affected.get("affectedProductName", "")
            ):
                if notice_id not in seen_notice_ids:
                    filtered_notices.append(notice)
                    seen_notice_ids.add(notice_id)
    return filtered_notices


@product_alerts_router.get(
    "/softwareFieldNotices",
    summary="Get field notices",
    description="Retrieve field notices",
)
@paginate
def field_notices_by_software(
    pagination: PaginationParams = Depends(),
    software_type: str = Query(
        ...,
        description="Filter by software type",
        enum=product_alerts.get_list_of_software_types(),
    ),
    software_version: str = Query(..., description="Filter by software version"),
) -> List[dict]:
    """Get all field notices, optionally filtered by product id, software type, and software version.
    :param pagination: Pagination parameters.
    :param software_type: Optional software type to filter field notices.
    :param software_version: Optional software version to filter field notices.
    :return: List of field notices.
    """
    software_types_list = list(set(product_alerts.get_list_of_software_types()))
    all_notices = product_alerts.get_list_of_fns()
    filtered_notices = []
    seen_notice_ids = set()

    for notice in all_notices:
        notice_id = notice.get("url")
        for affected in notice.get("productsAffected", []):
            if software_version == affected.get("affectedRelease", "") and (
                software_type in affected.get("affectedOsType", "")
                or software_type in affected.get("affectedSoftwareProduct", "")
            ):
                if notice_id not in seen_notice_ids:
                    filtered_notices.append(notice)
                    seen_notice_ids.add(notice_id)
    return filtered_notices


@product_alerts_router.get(
    "/allEndOfLifeDates",
    summary="Get all end Of Life Dates",
    description="Retrieve End of Life Dates",
)
@paginate
def end_of_life_all(pagination: PaginationParams = Depends()) -> List[dict]:

    return product_alerts.get_list_of_eols()


@product_alerts_router.get(
    "/hardwareEndOfLife",
    summary="Get end of life dates by product id",
    description="Retrieve End of Life Dates",
)
@paginate
def end_of_life_by_hardware(
    pagination: PaginationParams = Depends(),
    product_id: str = Query(..., description="Filter by product id"),
) -> List[dict]:

    all_eols = product_alerts.get_list_of_eols()
    filtered_eols = []
    seen_notice_ids = set()
    for eol in all_eols:
        bulletin_id = eol.get("url")
        # Check if product_id partially matches any entry in affectedProducts
        if (
                any(
                product_id
                in product for product in eol.get("affectedProducts", []))
                and bulletin_id not in seen_notice_ids
        ):
            filtered_eols.append(eol)
            seen_notice_ids.add(bulletin_id)
    return filtered_eols


@product_alerts_router.get(
    "/softwareEndOfLife",
    summary="Get software-related EOLs",
    description="Retrieve software-related EOLs",
)
@paginate
def end_of_life_by_software(
    pagination: PaginationParams = Depends(),
    software_type: str = Query(
        ..., description="Filter by software type", enum=["IOS XE", "IOS"]
    ),
    software_version: str = Query(..., description="Filter by software version"),
) -> List[dict]:
    all_eols = product_alerts.get_list_of_eols()
    filtered_eols = []
    seen_notice_ids = set()

    for eol in all_eols:
        # Get description and use descriptionLong if description is not available
        description = eol.get("description", "")
        if description:
            eol_id = eol.get("url")
            # Check if both software_type and software_version are in the description
            if software_type in description and software_version in description:
                if eol_id not in seen_notice_ids:
                    filtered_eols.append(eol)
                    seen_notice_ids.add(eol_id)

    return filtered_eols
