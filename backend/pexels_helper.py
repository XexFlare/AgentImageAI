import os
import requests

PEXELS_API_URL = "https://api.pexels.com/v1/search"


def search_images(query: str, per_page: int = 5) -> list[str]:
    response = requests.get(
        PEXELS_API_URL,
        headers={"Authorization": os.environ["PEXELS_API_KEY"]},
        params={"query": query, "per_page": per_page},
    )
    response.raise_for_status()
    photos = response.json().get("photos", [])
    return [photo["src"]["large"] for photo in photos]
