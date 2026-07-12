from __future__ import annotations

import json
from typing import Any

from .source_reader import ProducerPaperRecord

DEFAULT_INTEREST_SCORES = {
    "仅保留": 1,
    "非常一般": 2,
    "一般": 3,
    "感兴趣": 4,
    "非常感兴趣": 5,
}


def parse_list(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    text = str(raw_value or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]
    normalized = text.replace("|", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def interest_score(raw_value: str) -> int:
    return DEFAULT_INTEREST_SCORES.get(str(raw_value or "").strip(), 3)


def map_item_payload(record: ProducerPaperRecord) -> dict[str, Any]:
    payload = record.row_json if isinstance(record.row_json, dict) else {}
    canonical_url = str(record.article_url_norm or record.article_url or record.paper_article_url).strip()
    article_url = str(record.article_url or record.paper_article_url or record.article_url_norm).strip()
    journal = str(record.journal or record.paper_journal).strip()
    interest_level_value = str(record.interest_level or "").strip() or "一般"
    return {
        "literature_item_key": record.unique_key.strip(),
        "doi": str(record.doi or record.paper_doi).strip(),
        "canonical_url": canonical_url,
        "article_url": article_url,
        "journal": journal,
        "publish_date": record.publish_date,
        "publication_stage": str(payload.get("publication_stage") or "journal").strip() or "journal",
        "category": record.category or "other",
        "interest_level": interest_level_value,
        "interest_score": interest_score(interest_level_value),
        "interest_tag": record.interest_tag,
        "title_en": record.title_en,
        "title_zh": record.title_zh,
        "summary_zh": record.summary_zh,
        "abstract": record.abstract,
        "source_id": str(payload.get("source_id") or "").strip(),
        "publisher_family": str(payload.get("publisher_family") or "").strip(),
        "group_name": str(payload.get("group_name") or "").strip(),
        "authors_json": parse_list(payload.get("authors")),
        "tags_json": parse_list(record.tags or payload.get("tags")),
        "extra_json": payload,
    }


def map_membership_payload(record: ProducerPaperRecord, *, row_index: int) -> dict[str, Any]:
    payload = record.row_json if isinstance(record.row_json, dict) else {}
    publication_stage = str(payload.get("publication_stage") or "journal").strip() or "journal"
    decision = str(payload.get("llm_decision") or payload.get("review_final_decision") or "").strip()
    return {
        "literature_item_key": record.unique_key.strip(),
        "digest_date": record.digest_date,
        "list_type": record.list_type,
        "publication_stage": publication_stage,
        "decision": decision,
        "row_index": row_index,
        "source_record_json": payload,
    }
