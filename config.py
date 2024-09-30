import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Suppress httpx logs by setting their logging level to WARNING
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)