"""
This file contains the API and jobs main config, you can adjust the values without toughing the code
ACTIVE = TRUE/FALSE : job active/inactive
"""

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

    # Be carefully with this value, Cisco may block your IP for 24 hours
    # Lower it down if you are not in a rush,
    # DEFAULT_SEMAPHORE = 1 means 1 task at a time, http requests are still batched and executed asynchronously
    DEFAULT_SEMAPHORE = 10

    def __init__(self):
        """Initialize configuration and create the project data directory."""
        # Ensure the directory exists when the class is instantiated
        self.PROJECT_DATA_DIR.mkdir(exist_ok=True, parents=True)


class GetFeaturesConfig(Config):
    ACTIVE = False

    FETCH_PLATFORMS_ONLINE = True
    FETCH_RELEASES_ONLINE = True
    FETCH_FEATURES_ONLINE = True

    # with 3 you have 16m combinations, increase this value if you have more features to avoid duplications
    # although baer in mind that this significantly increase the archive size (longer has strings)
    HASHING_DIGEST = 3

    # Be carefully with this value, Cisco may block your IP for 24 hours
    CONCURRENT_REQUESTS_LIMIT = 5
    REQUEST_DELAY = 1
    ARCHIVE_FILENAME = "features_data.tar.gz"
    UNIQUE_FEATURES_FILENAME = "unique_features.json"
    FEATURES_DIR: Path = Config.PROJECT_DATA_DIR / "features"
    TYPES = [ptype.value for ptype in PlatformTypes]
    HEADERS = {}
    REQUEST_1 = "https://cfnngws.cisco.com/api/v1/platform"
    REQUEST_2 = "https://cfnngws.cisco.com/api/v1/release"
    REQUEST_3 = "https://cfnngws.cisco.com/api/v1/by_product_result"

    def __init__(self):
        """Initialize configuration and create the project data directory."""
        # Ensure the directory exists when the class is instantiated
        super().__init__()
        self.FEATURES_DIR.mkdir(exist_ok=True, parents=True)


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
    EOL_FILE_NAME = "eol.json"
    # Archiving
    COMPRESSION_LEVEL = 9
    ARCHIVE_FILE = "eol_data.tar.gz"

    # Refreshing cashing in seconds
    DATA_REFRESH_INTERVAL = 60 * 60  # 1 hour

    CATEGORIES_JSON_PATH = os.path.join(BASE_FOLDER, "products_by_category.json")
