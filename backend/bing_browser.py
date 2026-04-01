import json
from playwright.sync_api import sync_playwright

BING_SEARCH_URL = "https://www.bing.com/images/search"


def search_bing_images_browser(query: str, count: int = 10) -> list:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BING_SEARCH_URL}?q={query}")
            page.wait_for_selector("a.iusc", timeout=10000)

            anchors = page.query_selector_all("a.iusc")
            results = []
            for anchor in anchors:
                if len(results) >= count:
                    break
                m_attr = anchor.get_attribute("m") or ""
                if not m_attr:
                    continue
                try:
                    meta = json.loads(m_attr)
                    murl = meta.get("murl", "")
                except (json.JSONDecodeError, ValueError):
                    continue
                if not murl:
                    continue
                results.append({"url": murl, "query": query, "source": "bing_browser"})

            browser.close()
            return results
    except Exception:
        return []
