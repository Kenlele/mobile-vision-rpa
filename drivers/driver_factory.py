"""
drivers/driver_factory.py
Factory module for creating iOS and mock device driver instances.
"""

import logging
from drivers.base_driver import BaseDriver
from drivers.ios_driver import IOSDriver

logger = logging.getLogger("DriverFactory")


class DriverFactory:
    """Factory class to create target device drivers."""

    @staticmethod
    def create_driver(driver_type: str = "ios", udid: str = "booted") -> BaseDriver:
        """
        Create driver instance based on requested type.
        Supports 'ios' (Xcode iOS Simulator) and 'mock' driver modes.
        """
        driver_type_lower = driver_type.lower() if driver_type else "ios"

        if driver_type_lower == "ios":
            logger.info(f"Initializing Xcode iOS Simulator Driver (UDID: {udid})")
            return IOSDriver(udid=udid, mock_fallback=False)

        if driver_type_lower in ["iphone_mirror", "mirror"]:
            from drivers.iphone_mirror_driver import IPhoneMirrorDriver
            logger.info("Initializing macOS iPhone Mirroring Driver (Physical Device via Mirror)")
            return IPhoneMirrorDriver(mock_fallback=False)

        if driver_type_lower != "mock":
            logger.warning(f"Unsupported driver type '{driver_type}'. Defaulting to Mock iOS Driver.")

        logger.info("Initializing Mock Driver (iOS Simulator fallback mode)")
        return IOSDriver(udid="mock", mock_fallback=True)



