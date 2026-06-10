import logging


logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# httpx logs every proxied request at INFO; quiet it to drop per-chart log spam
logging.getLogger("httpx").setLevel(logging.WARNING)
