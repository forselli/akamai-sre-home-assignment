import json
import logging
import time
from typing import Optional

import httpx
from cache import (
    REQUEST_TIMEOUT,
    redis_client,
    redis_ttl,
)
from database import save_characters_to_db
from exceptions import ServiceUnavailableException
from fastapi import HTTPException
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential
from utils import CACHE_HITS, CACHE_MISSES, CHARACTERS_PROCESSED

logger = logging.getLogger(__name__)


def main(db: Session):
    BASE_URL = "https://rickandmortyapi.com/api/character?species=Human&status=Alive&page="
    all_data_results = []
    page = 1

    try:
        # Check if data is already in Redis
        cached_characters = redis_client.get("characters")
        if cached_characters:
            CACHE_HITS.labels(app_name="fastapi-app").inc()
            return json.loads(cached_characters.decode("utf-8"))

        CACHE_MISSES.labels(app_name="fastapi-app").inc()

        # Fetch the first page outside the loop to get the total number of pages
        characters = fetch_characters(BASE_URL, page)

        total_pages = characters["info"]["pages"]
        logger.info(f"Total pages to fetch: {total_pages}")

        # Process the first page
        filtered_characters = list(filter_request(characters["results"]))
        all_data_results.extend(filtered_characters)
        CHARACTERS_PROCESSED.labels(app_name="fastapi-app").inc(len(filtered_characters))
        logger.info(f"Processing page {page} from {total_pages}")

        # Iterate through the remaining pages
        for page in range(2, total_pages + 1):
            try:
                characters = fetch_characters(BASE_URL, page)
                if not characters:
                    logger.warning(f"Failed to fetch page {page}, stopping pagination")
                    break
                filtered_characters = list(filter_request(characters["results"]))
                all_data_results.extend(filtered_characters)
                CHARACTERS_PROCESSED.labels(app_name="fastapi-app").inc(len(filtered_characters))
                logger.info(f"Processing page {page} from {total_pages}")
            except Exception as e:
                logger.error(f"Error processing page {page}: {str(e)}")
                # Continue with next page instead of failing completely
                continue

        if not all_data_results:
            logger.info("No Earth characters found")

        # Save to database and Redis
        save_characters_to_db(all_data_results, db)
        redis_client.set("characters", json.dumps(all_data_results), ex=redis_ttl)
        logger.info(f"Successfully saved {len(all_data_results)} characters to database and cache")
        return all_data_results

    except Exception as e:
        logger.error(f"Error in main processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def fetch_characters(url: str, page: int) -> Optional[dict]:
    """
    Fetch characters from the Rick and Morty API with retry logic and rate limiting.
    """
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(url + str(page))
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:  # Too Many Requests
            retry_after = int(exc.response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limited by API. Waiting {retry_after} seconds.")
            time.sleep(retry_after)
            return fetch_characters(url, page)
        raise ServiceUnavailableException("The Rick and Morty API is unavailable")
    except httpx.RequestError as exc:
        logger.error(f"Request error: {exc}")
        raise ServiceUnavailableException("The Rick and Morty API is unavailable")


def filter_request(characters):
    """Filter the characters to only include Earth characters."""
    for character in characters:
        if "Earth" in character["origin"]["name"]:
            yield character
