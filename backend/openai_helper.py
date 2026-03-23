import logging
import os
import json
from openai import OpenAI

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a JSON-only response bot. You must always respond with valid JSON and nothing else — no explanation, no markdown, no code blocks.

Given a user message, determine the intent.

Return exactly this structure:
{
  "intent": "new_search" | "add_fields",
  "fields": ["..."]
}

Rules:
- "intent" is "new_search" if the user wants to search for images with a new subject or concept.
- "intent" is "add_fields" if the user wants to add or change metadata fields on existing results.
- "fields" lists metadata field names mentioned by the user (empty list for "new_search").
- Never include any text outside the JSON object."""


PLAN_PROMPT = """You are a JSON-only response bot. You must always respond with valid JSON and nothing else — no explanation, no markdown, no code blocks.

Given a user search request, decide what type of input it is and produce 3–5 concrete items to search for.

Return exactly this structure:
{
  "input_type": "...",
  "items": ["...", "..."]
}

Rules:
- "input_type" is a short label for the category of the input (e.g. "real-world entities", "visual variations", "structured items", "character styles").
- "items" are specific, searchable things derived from the user's request.
- Each item should be a concise, image-search-friendly phrase.
- Generate 3–5 items that give diverse and useful coverage of the topic.
- Never include any text outside the JSON object.

Examples:
  input: "airports"       → input_type: "real-world entities", items: ["JFK Airport", "Heathrow Airport", "Dubai Airport", "LAX Airport"]
  input: "anime styles"   → input_type: "visual variations",   items: ["shonen anime style", "studio ghibli style", "isekai anime aesthetic"]
  input: "sports cars"    → input_type: "structured items",    items: ["Ferrari 488", "Lamborghini Huracan", "Porsche 911", "McLaren 720S"]"""


def plan_search(message: str) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": PLAN_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.4,
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("plan_search: failed to parse JSON response: %r", raw)
        return {"input_type": "unknown", "items": [message]}


def interpret_message(message: str) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.4,
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)
