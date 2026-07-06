import os
import json
import re
import time

import pdfplumber

from app.celery_app import celery_app
from app.config import OUTPUT_DIR


@celery_app.task(bind=True, name="app.tasks.process_chunk", max_retries=2, default_retry_delay=5)
def process_chunk(self, chunk_meta: dict):
    """
    Worker task: runs in its own process (potentially on a different
    machine). Extracts text page-by-page from one 20-page chunk PDF,
    computes simple stats, and writes a per-chunk JSON result.

    This is where you'd plug in heavier work later (LLM summarization,
    NER, embeddings, etc.) without touching the orchestration code.
    """
    chunk_id = chunk_meta["chunk_id"]
    chunk_path = chunk_meta["path"]

    try:
        pages_out = []
        full_text_parts = []

        with pdfplumber.open(chunk_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                page_number = chunk_meta["start_page"] + i
                pages_out.append({
                    "page_number": page_number,
                    "char_count": len(text),
                    "word_count": len(text.split()),
                    "text": text,
                })
                full_text_parts.append(text)

        full_text = "\n".join(full_text_parts)
        word_count = len(full_text.split())

        result = {
            "chunk_id": chunk_id,
            "source_file": chunk_meta.get("source_file"),
            "start_page": chunk_meta["start_page"],
            "end_page": chunk_meta["end_page"],
            "page_count": chunk_meta["page_count"],
            "word_count": word_count,
            "char_count": len(full_text),
            "processed_at": time.time(),
            "pages": pages_out,
        }

        results_dir = os.path.join(OUTPUT_DIR, "results")
        os.makedirs(results_dir, exist_ok=True)
        result_path = os.path.join(results_dir, f"chunk_{chunk_id:04d}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return {"chunk_id": chunk_id, "result_path": result_path, "status": "done"}

    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.merge_results")
def merge_results(chunk_task_results: list, source_file: str, output_name: str = "book_full.json"):
    """
    Runs after all process_chunk tasks finish (via a Celery `chord`).
    Reads every per-chunk JSON file and stitches them into one ordered
    JSON document for the whole book.
    """
    merged = {
        "source_file": source_file,
        "num_chunks": len(chunk_task_results),
        "chunks": [],
    }

    ordered = sorted(chunk_task_results, key=lambda r: r["chunk_id"])
    for r in ordered:
        with open(r["result_path"], "r", encoding="utf-8") as f:
            merged["chunks"].append(json.load(f))

    merged["total_pages"] = sum(c["page_count"] for c in merged["chunks"])
    merged["total_word_count"] = sum(c["word_count"] for c in merged["chunks"])

    out_path = os.path.join(OUTPUT_DIR, output_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return {"output_path": out_path, "num_chunks": len(merged["chunks"])}
