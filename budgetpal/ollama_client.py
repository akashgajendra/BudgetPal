import re
import time

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma3:4b"
BATCH_SIZE = 20
TIMEOUT = 30


def is_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


def _build_prompt(descriptions: list[str], categories: list[str]) -> str:
    cats = ", ".join(categories)
    lines = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(descriptions))
    return (
        "You are a personal finance transaction categorizer.\n"
        f"Valid categories: {cats}\n\n"
        "For each numbered transaction, reply with ONLY the number and category, one per line:\n"
        "1: groceries\n"
        "2: dining\n\n"
        f"Transactions:\n{lines}"
    )


_RESPONSE_RE = re.compile(r"^(\d+)\s*[:.]\s*(.+)$", re.MULTILINE)


def _parse_response(text: str, descriptions: list[str], valid: set[str]) -> dict[int, str]:
    result = {}
    for match in _RESPONSE_RE.finditer(text):
        idx = int(match.group(1)) - 1
        cat = match.group(2).strip().lower().replace(" ", "_")
        if 0 <= idx < len(descriptions) and cat in valid:
            result[idx] = cat
    return result


def categorize_batch(
    descriptions: list[str],
    categories: list[str],
) -> dict[int, str]:
    valid = set(categories)
    prompt = _build_prompt(descriptions, categories)
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    for attempt in range(2):
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            text = r.json().get("response", "")
            return _parse_response(text, descriptions, valid)
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == 0:
                time.sleep(2)
    return {}
