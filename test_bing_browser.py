import sys
sys.path.insert(0, ".")

from backend.bing_browser import search_bing_images_browser

query = "sunbird waterfront salima malawi"
results = search_bing_images_browser(query)

print(f"Query: {query}")
print(f"Results found: {len(results)}\n")
for i, r in enumerate(results, 1):
    print(f"[{i}] URL:    {r['url']}")
    print(f"     Source: {r['source']}")
    print()
