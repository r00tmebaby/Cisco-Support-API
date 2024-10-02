from fastapi import APIRouter, Depends

from app.config import Config, GetEOLConfig, logging
from app.models import Platform, ProductAlerts
from app.utils import PaginationParams, ProductAlertsExtractor, paginate

product_alerts_router = APIRouter(prefix="/productAlerts", tags=["Product Alerts"])

logger = logging.getLogger("product_alerts")

# Create a global instance of ProductAlertsExtractor for accessing tar file
product_alerts_extractor = ProductAlertsExtractor(
    tar_path=Config.PROJECT_DATA_DIR / GetEOLConfig.ARCHIVE_FILE
)


@product_alerts_router.get(
    "/field_notices",
    summary="Get field notices",
    description="Retrieve field notices",
)
@paginate
def field_notices(
    platform: ProductAlerts = Depends(), pagination: PaginationParams = Depends()
): ...
