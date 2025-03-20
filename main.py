import time

import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()
BASE_URL = "https://rickandmortyapi.com/api/character"


# Function to query the API with retries for transient failures
def fetch_characters_with_retries(url, retries=3, backoff_factor=2):
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code in [
            429,
            500,
            502,
            503,
            504,
        ]:  # Handle rate limits and server errors
            time.sleep(backoff_factor**attempt)
        else:
            response.raise_for_status()
    raise HTTPException(
        status_code=503, detail="Service unavailable after multiple retries"
    )


@app.get("/characters")
def get_filtered_characters():
    characters = []
    page = 1

    while True:
        url = f"{BASE_URL}?species=Human&status=Alive&page={page}"
        data = fetch_characters_with_retries(url)
        if not data or "results" not in data:
            break

        for character in data["results"]:
            if "Earth" in character["origin"]["name"]:
                characters.append(
                    {
                        "id": character["id"],
                        "name": character["name"],
                        "status": character["status"],
                        "species": character["species"],
                        "origin": character["origin"]["name"],
                        "image": character["image"],
                    }
                )

        if not data.get("info", {}).get("next"):
            break
        page += 1

    return {"count": len(characters), "characters": characters}
