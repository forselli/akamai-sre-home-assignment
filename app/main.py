import json
import logging
import os
import time
from datetime import datetime
from typing import List, Optional

import httpx
import redis
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from . import models
from .database import engine, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Connect to Redis
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)), db=0
)
redis_ttl = int(os.getenv("REDIS_TTL", 30))

# API Configuration
API_RATE_LIMIT = 20  # requests per minute
API_RATE_WINDOW = 60  # seconds
REQUEST_TIMEOUT = 30  # seconds


def is_rate_limited() -> bool:
    """Check if we're rate limited by counting requests in Redis."""
    current = redis_client.get("api_request_count")
    if current is None:
        redis_client.setex("api_request_count", API_RATE_WINDOW, 1)
        return False

    count = int(current)
    if count >= API_RATE_LIMIT:
        return True

    redis_client.incr("api_request_count")
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def fetch_characters(url: str, page: int) -> Optional[dict]:
    """
    Fetch characters from the Rick and Morty API with retry logic and rate limiting.
    """
    if is_rate_limited():
        wait_time = redis_client.ttl("api_request_count")
        logger.warning(f"Rate limited. Waiting {wait_time} seconds before retrying.")
        time.sleep(wait_time)
        return fetch_characters(url, page)

    logger.info(f"Fetching page {page}")
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
        logger.error(
            f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
        )
        raise
    except httpx.RequestError as exc:
        logger.error(f"Request error: {exc}")
        raise


def filter_request(characters):
    for character in characters:
        if "Earth" in character["origin"]["name"]:
            # print(
            #     f"Found character {character['name']} on {character['origin']['name']}"
            # )
            yield character


def save_characters_to_db(characters: List[dict], db: Session):
    for character in characters:
        db_character = models.Character(
            id=character.get("id"),
            name=character.get("name", ""),
            status=character.get("status", ""),
            species=character.get("species", ""),
            type=character.get("type", ""),
            gender=character.get("gender", ""),
            origin=character.get("origin", {}),
            location=character.get("location", {}),
            image=character.get("image", ""),
            episode=character.get("episode", []),
            url=character.get("url", ""),
            created=character.get("created"),
        )
        db.add(db_character)
    db.commit()


def main(db: Session):
    BASE_URL = (
        "https://rickandmortyapi.com/api/character?species=Human&status=Alive&page="
    )
    all_data_results = []
    page = 1

    try:
        # Fetch the first page outside the loop to get the total number of pages
        characters = fetch_characters(BASE_URL, page)
        if not characters:
            raise HTTPException(status_code=500, detail="Failed to fetch initial data")

        total_pages = characters["info"]["pages"]
        logger.info(f"Total pages to fetch: {total_pages}")

        # Process the first page
        data_results = list(filter_request(characters["results"]))
        all_data_results.extend(data_results)
        logger.info(
            f"Processed page {page}, found {len(data_results)} Earth characters"
        )

        # Iterate through the remaining pages
        for page in range(2, total_pages + 1):
            try:
                characters = fetch_characters(BASE_URL, page)
                if not characters:
                    logger.warning(f"Failed to fetch page {page}, stopping pagination")
                    break
                data_results = list(filter_request(characters["results"]))
                all_data_results.extend(data_results)
                logger.info(
                    f"Processed page {page}, found {len(data_results)} Earth characters"
                )
            except Exception as e:
                logger.error(f"Error processing page {page}: {str(e)}")
                # Continue with next page instead of failing completely
                continue

        if not all_data_results:
            raise HTTPException(status_code=500, detail="No Earth characters found")

        # Save to database
        save_characters_to_db(all_data_results, db)
        logger.info(
            f"Successfully saved {len(all_data_results)} characters to database"
        )
        return all_data_results

    except Exception as e:
        logger.error(f"Error in main processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters")
async def get_characters(db: Session = Depends(get_db)):
    try:
        cached_characters = redis_client.get("characters")
        if cached_characters:
            logger.info("Returning cached characters")
            return json.loads(cached_characters.decode("utf-8"))

        logger.info("Fetching characters")
        characters = main(db)
        # Store the item in Redis with TTL from environment variable
        redis_client.set("characters", json.dumps(characters), ex=redis_ttl)
        return characters
    except Exception as e:
        logger.error(f"Error in get_characters endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
