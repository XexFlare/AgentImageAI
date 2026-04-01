from dotenv import load_dotenv
load_dotenv()

import json
import time
import urllib.request
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.openai_helper import interpret_message, plan_search
from backend.pexels_helper import search_images
from backend.image_downloader import download_images

DEV_MODE = True

USAGE_FILE = Path("usage_data.json")
RATE_LIMIT = 5
WINDOW_SECONDS = 24 * 60 * 60

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8007"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="images"), name="images")


class ChatRequest(BaseModel):
    message: str


def load_usage() -> dict:
    if not USAGE_FILE.exists():
        return {}
    try:
        return json.loads(USAGE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_usage(data: dict):
    USAGE_FILE.write_text(json.dumps(data, indent=2))


def fetch_country(ip: str) -> str:
    try:
        with urllib.request.urlopen(f"https://ipapi.co/{ip}/json/", timeout=3) as resp:
            return json.loads(resp.read()).get("country_name", "Unknown")
    except Exception:
        return "Unknown"


def check_rate_limit(ip: str):
    data = load_usage()
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    if ip not in data:
        country = fetch_country(ip)
        data[ip] = {"timestamps": [], "country": country}

    data[ip]["timestamps"] = [t for t in data[ip]["timestamps"] if t > cutoff]

    if len(data[ip]["timestamps"]) >= RATE_LIMIT:
        save_usage(data)
        raise HTTPException(status_code=429, detail="Daily search limit reached")

    data[ip]["timestamps"].append(now)
    save_usage(data)


@app.get("/")
def root():
    return {"message": "AgentImage AI running"}


@app.post("/chat")
def chat(request: ChatRequest, http_request: Request):
    if not DEV_MODE:
        ip = http_request.client.host
        check_rate_limit(ip)

    try:
        result = interpret_message(request.message)
        saved_paths = []
        if result.get("intent") == "new_search":
            plan = plan_search(request.message)
            batches = [(search_images(f"{request.message} {item}"), item) for item in plan["items"]]
            saved_paths = download_images(batches, topic=request.message, input_type=plan["input_type"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"result": result, "images": saved_paths}
