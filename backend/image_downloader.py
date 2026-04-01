import csv
import os
import re
from pathlib import Path
import requests

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")


def _slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r"[^\w]+", "_", text).strip("_")


def _next_dataset_dir(topic_dir: str, base_name: str) -> tuple[str, str]:
    """Return (dataset_path, dataset_name) for the next available run number."""
    index = 1
    while True:
        name = f"{base_name}_{index}"
        path = os.path.join(topic_dir, name)
        if not os.path.exists(path):
            return path, name
        index += 1


def download_images(
    batches: list[tuple[list[str], str]],
    topic: str,
    input_type: str,
) -> list[str]:
    """Download images for multiple (urls, item) batches into a versioned dataset folder.

    Args:
        batches:    list of (urls, item) tuples where item is the planned search term
        topic:      original user message, used to name the dataset folder
        input_type: category label from the planning stage (e.g. "real-world entities")

    Returns:
        list of saved filenames
    """
    base_name = _slugify(topic)
    topic_dir = os.path.join(IMAGES_DIR, base_name)
    dataset_path, dataset_name = _next_dataset_dir(topic_dir, base_name)
    os.makedirs(dataset_path)

    rows = []
    image_index = 1

    for urls, item in batches:
        for img in urls:
            url = img["url"]
            raw_ext = os.path.splitext(url.split("?")[0])[-1].lower()
            ext = raw_ext if raw_ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
            filename = f"{dataset_name}_{image_index}{ext}"
            filepath = os.path.join(dataset_path, filename)
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(response.content)
            except Exception as e:
                print(f"[skip] Failed to download {url}: {e}")
                continue
            relative_path = str(Path(filepath).resolve().relative_to(Path(IMAGES_DIR).resolve())).replace("\\", "/")
            rows.append({"filename": filename, "relative_path": relative_path, "item": item, "input_type": input_type, "original_query": topic})
            image_index += 1

    csv_path = os.path.join(dataset_path, f"{dataset_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "relative_path", "item", "input_type", "original_query"])
        writer.writeheader()
        writer.writerows(rows)

    return [row["relative_path"] for row in rows]
