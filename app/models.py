from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ProductAlerts(BaseModel):
    product_name: Optional[str] = None
    product_id: Optional[str] = None
    software_type: Optional[str] = None
    software_version: Optional[str] = None


class PlatformTypes(str, Enum):
    """Enum representing different types of platforms."""

    Switches = "Switches"
    Routers = "Routers"
    Wireless = "Wireless"
    IOT_Routers = "IOT Routers"
    IOT_Switches = "IOT Switches"


class Platform(BaseModel):
    by_name: Optional[str] = None
    platform_choice: PlatformTypes = PlatformTypes.Switches


class FeaturesRequestModel(BaseModel):
    platform_id: Optional[int] = None
    mdf_product_type: Optional[str] = None
    release_id: Optional[int] = None
    feature_set_id: Optional[int] = None
