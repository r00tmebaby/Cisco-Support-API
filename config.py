import logging
import os
from pathlib import Path

from models import PlatformTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Suppress httpx logs by setting their logging level to WARNING
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


class Config:
    """Base configuration class with data directory setup."""

    PROJECT_DATA_DIR = Path(os.path.join(os.getcwd(), "data"))
    CISCO_ROOT_URL = "https://www.cisco.com"
    CISCO_SUPPORT_URL = CISCO_ROOT_URL + "/c/en/us/support/"
    DEFAULT_SEMAPHORE = 10

    def __init__(self):
        """Initialize configuration and create the project data directory."""
        # Ensure the directory exists when the class is instantiated
        self.PROJECT_DATA_DIR.mkdir(exist_ok=True, parents=True)


class GetFeaturesConfig(Config):
    ACTIVE = True

    FETCH_PLATFORMS_ONLINE = True
    FETCH_RELEASES_ONLINE = True
    FETCH_FEATURES_ONLINE = False

    CONCURRENT_REQUESTS_LIMIT = 10
    REQUEST_DELAY = 1
    FEATURES_DIR: Path = Config.PROJECT_DATA_DIR
    TYPES = [ptype.value for ptype in PlatformTypes]
    HEADERS = {}
    REQUEST_1 = "https://cfnngws.cisco.com/api/v1/platform"
    REQUEST_2 = "https://cfnngws.cisco.com/api/v1/release"
    REQUEST_3 = "https://cfnngws.cisco.com/api/v1/by_product_result"


class GetEOLConfig(Config):
    ACTIVE = False

    FIELD_NOTICES_LINK = "products-field-notices-list.html"
    EOS_EOS_NOTICES_LINK = "eos-eol-notice-listing.html"
    CISCO_SUPPORT_URL = f"{Config.CISCO_SUPPORT_URL}/index.html"

    CONCURRENT_REQUESTS = Config.DEFAULT_SEMAPHORE
    TIMEOUT_THREAD = 1
    TIMEOUT_REQUESTS = 1

    BASE_FOLDER = Config.PROJECT_DATA_DIR
    EOL_FOLDER = os.path.join(BASE_FOLDER, "eol-eos")

    # Archiving
    COMPRESSION_LEVEL = 9
    ARCHIVE_FILE = "eol_data.tar.gz"

    CATEGORIES_JSON_PATH = os.path.join(BASE_FOLDER, "products_by_category.json")
