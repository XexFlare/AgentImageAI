from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.openai_helper import interpret_message, plan_search
from backend.pexels_helper import search_images
from backend.image_downloader import download_images

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"message": "AgentImage AI running"}


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        result = interpret_message(request.message)
        saved_paths = []
        if result.get("intent") == "new_search":
            plan = plan_search(request.message)
            batches = [(search_images(f"{request.message} {item}"), item) for item in plan["items"]]
            saved_paths = download_images(batches, topic=request.message, input_type=plan["input_type"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"result": result, "images": saved_paths}
