import json
import os
import time
from utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = "data/cache"
CACHE_TTL  = 86400  # 24 hours in seconds


def _cache_path(slug: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{slug.upper()}.json")


def load_cache(slug: str) -> dict | None:
    path = _cache_path(slug)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        age = time.time() - data.get("_cached_at", 0)
        if age > CACHE_TTL:
            logger.info(f"Cache expired for {slug} ({age/3600:.1f}h old)")
            return None
        logger.info(f"Cache hit for {slug} ({age/60:.0f}m old)")
        return data
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
        return None


def save_cache(slug: str, data: dict) -> None:
    path = _cache_path(slug)
    try:
        data["_cached_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Cache saved → {path}")
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


def clear_cache(slug: str) -> None:
    path = _cache_path(slug)
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Cache cleared for {slug}")