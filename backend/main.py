from dotenv import load_dotenv
load_dotenv()

import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


USERS_FILE = Path("users.json")


class ChatRequest(BaseModel):
    message: str
    max_images: int = 20


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


IMAGES_DIR = Path("images")


@app.get("/download/{folder:path}")
def download_dataset(folder: str):
    dataset_path = (IMAGES_DIR / folder).resolve()
    if not dataset_path.exists() or not dataset_path.is_dir():
        raise HTTPException(status_code=404, detail="Dataset folder not found")
    if not str(dataset_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid folder path")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in dataset_path.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(dataset_path))
    buf.seek(0)

    zip_name = dataset_path.name + ".zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_name}"},
    )


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(request: LoginRequest):
    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    user = next(
        (u for u in users if u["username"] == request.username and u["password"] == request.password),
        None,
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "username": user["username"],
        "firstname": user["firstname"],
        "lastname": user["lastname"],
        "jobTitle": user["jobTitle"],
    }


@app.get("/")
def root():
    return {"message": "AgentImage AI running"}


@app.post("/chat-stream")
def chat_stream(request: ChatRequest, http_request: Request):
    if not DEV_MODE:
        ip = http_request.client.host
        check_rate_limit(ip)

    items = [line.strip() for line in request.message.splitlines() if line.strip()]
    if not items:
        items = [request.message.strip()]

    def event_stream():
        groups = []
        dataset_folder = None
        for item in items:
            yield json.dumps({"event": "start", "label": item}) + "\n"
            try:
                result = interpret_message(item)
                if result.get("intent") == "new_search":
                    plan = plan_search(item)
                    batches = [(search_images(f"{item} {term}"), term) for term in plan["items"]]
                    saved_paths, dataset_folder = download_images(batches, topic=item, input_type=plan["input_type"], max_images=request.max_images)
                    groups.append({"label": item, "images": saved_paths})
            except Exception as e:
                yield json.dumps({"event": "error", "label": item, "detail": str(e)}) + "\n"
                continue
            yield json.dumps({"event": "done", "label": item}) + "\n"
        yield json.dumps({"event": "complete", "groups": groups, "dataset_folder": dataset_folder}) + "\n"

    return StreamingResponse(event_stream(), media_type="text/plain")
