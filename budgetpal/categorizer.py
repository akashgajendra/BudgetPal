from dataclasses import dataclass, field
from pathlib import Path

import yaml

from budgetpal import ollama_client
from budgetpal.parser import Transaction

DEFAULT_RULES = Path(__file__).resolve().parent.parent / "categories.yaml"
UNCATEGORIZED = "other"


@dataclass
class CategorizeResult:
    rows: list[dict] = field(default_factory=list)
    ollama_used: bool = False
    ollama_warning: str | None = None
    unmatched_count: int = 0


def load_rules(path: Path = DEFAULT_RULES) -> dict[str, list[str]]:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return {cat: [k.lower() for k in kws] for cat, kws in raw.items()}


def _keyword_match(description: str, rules: dict[str, list[str]]) -> str:
    text = description.lower()
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return UNCATEGORIZED


def categorize(
    transactions: list[Transaction],
    rules: dict[str, list[str]] | None = None,
    use_ollama: bool = True,
) -> CategorizeResult:
    rules = rules if rules is not None else load_rules()
    rows = [
        {
            "date": t.date,
            "description": t.description,
            "amount": t.amount,
            "category": _keyword_match(t.description, rules),
        }
        for t in transactions
    ]

    unmatched = [i for i, r in enumerate(rows) if r["category"] == UNCATEGORIZED]
    result = CategorizeResult(rows=rows, unmatched_count=len(unmatched))

    if not unmatched or not use_ollama:
        return result

    if not ollama_client.is_available():
        result.ollama_warning = (
            f"Ollama is not running at {ollama_client.OLLAMA_URL}. "
            f"{len(unmatched)} transaction(s) could not be categorized by AI and are labeled 'other'."
        )
        return result

    categories = list(rules.keys())
    for batch_start in range(0, len(unmatched), ollama_client.BATCH_SIZE):
        batch_indices = unmatched[batch_start : batch_start + ollama_client.BATCH_SIZE]
        descriptions = [rows[i]["description"] for i in batch_indices]
        assignments = ollama_client.categorize_batch(descriptions, categories)
        for pos, cat in assignments.items():
            rows[batch_indices[pos]]["category"] = cat

    still_unmatched = sum(1 for r in rows if r["category"] == UNCATEGORIZED)
    result.ollama_used = True
    result.unmatched_count = still_unmatched
    if still_unmatched:
        result.ollama_warning = f"AI categorized most transactions, but {still_unmatched} remain as 'other'."
    return result
