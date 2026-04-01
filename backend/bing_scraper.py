import re
import requests

BING_SEARCH_URL = "https://www.bing.com/images/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def search_bing_images(query: str, count: int = 10) -> list:
    try:
        response = requests.get(BING_SEARCH_URL, headers=HEADERS, params={"q": f'"{query}" hotel building exterior'})
        response.raise_for_status()
    except Exception:
        return []

    blocks = re.findall(r'"m"\s*:\s*\{[^}]*"murl"\s*:\s*"(https?://[^"]+)"[^}]*\}', response.text)
    results = []
    for url in blocks:
        if len(results) >= count:
            break
        results.append({"url": url, "query": query, "source": "bing"})

    return results
