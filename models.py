from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PlatformTypes(str, Enum):
    Switches = "Switches"
    Routers = "Routers"
    Wireless = "Wireless"
    IOT_Routers = "IOT Routers"
    IOT_Switches = "IOT Switches"


class Platform(BaseModel):
    by_name: Optional[str] = None
    platform_choice: PlatformTypes = PlatformTypes.Switches
