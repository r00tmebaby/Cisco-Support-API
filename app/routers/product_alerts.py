import os
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.params import Query

from app.config import Config, GetEOLConfig, logging
from app.models import Platform, ProductAlerts
from app.utils import PaginationParams, ProductAlertsExtractor, paginate

product_alerts_router = APIRouter(prefix="/productAlerts", tags=["Product Alerts"])

logger = logging.getLogger("product_alerts")

# Create a global instance of ProductAlertsExtractor for accessing tar file
product_alerts_extractor = ProductAlertsExtractor(
    tar_path=str(os.path.join(Config.PROJECT_DATA_DIR, GetEOLConfig.ARCHIVE_FILE))
)
product_alerts_extractor.load_tar_file()


@product_alerts_router.get(
    "/field_notices", summary="Get field notices", description="Retrieve field notices"
)
@paginate
def field_notices(
    pagination: PaginationParams = Depends(),
    product_id: Optional[str] = Query(None, description="Filter by product id"),
) -> List[dict]:
    """
    Get all field notices, optionally filtered by product id, software type, and software version.
    :param pagination: Pagination parameters.
    :param product_id: Optional product id to filter field notices.
    :return: List of field notices.
    """
    # Extract all field notices from the data source (tar file or database)
    all_alerts = product_alerts_extractor.extract_products_eol()
    filtered_notices = []
    # Loop through all alerts
    for alert in all_alerts:
        notices = alert.get("FNS", [])
        for notice in notices:
            for affected in notice.get("productsAffected", []):
                if (
                    product_id and product_id in affected.get("affectedProductId", "")
                ) or (
                    product_id and product_id in affected.get("affectedProductName", "")
                ):
                    filtered_notices.append(notice)
        if filtered_notices:
            return filtered_notices
    # Return all notices if no filtering criteria are matched
    return all_alerts
