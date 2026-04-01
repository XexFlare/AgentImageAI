import os
import requests
from backend.bing_browser import search_bing_images_browser

PEXELS_API_URL = "https://api.pexels.com/v1/search"


def search_images(query: str, per_page: int = 5) -> list[str]:
    response = requests.get(
        PEXELS_API_URL,
        headers={"Authorization": os.environ["PEXELS_API_KEY"]},
        params={"query": query, "per_page": per_page},
    )
    response.raise_for_status()
    photos = response.json().get("photos", [])
    pexels_results = [{"url": photo["src"]["large"], "query": query, "source": "pexels"} for photo in photos]
    bing_results = search_bing_images_browser(query)
    return pexels_results + bing_results
