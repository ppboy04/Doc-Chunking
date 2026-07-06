"""
Orchestrator / CLI entry point.

Usage:
    python -m app.main /data/input/book.pdf

Flow:
  1. Split the source PDF into 20-page chunk PDFs      (chunker.py)
  2. Fan the chunks out to Celery workers in parallel  (tasks.process_chunk)
  3. Wait for all of them (a Celery "chord")
  4. Merge every chunk's JSON into one final book-level JSON
"""
import sys
import json
import time

from celery import chord

from app.chunker import split_pdf_into_chunks
from app.tasks import process_chunk, merge_results
from app.config import OUTPUT_DIR


def run(pdf_path: str, poll_interval: float = 1.0):
    print(f"[1/3] Splitting {pdf_path} into chunks...")
    manifest = split_pdf_into_chunks(pdf_path)
    print(f"      -> {manifest['num_chunks']} chunks "
          f"({manifest['total_pages']} pages, {manifest['chunk_size']} pages/chunk)")

    manifest_path = f"{OUTPUT_DIR}/manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("[2/3] Dispatching chunks to Celery workers (parallel)...")
    job = chord(
        (process_chunk.s(c) for c in manifest["chunks"]),
        merge_results.s(source_file=pdf_path),
    )
    async_result = job.apply_async()

    print("      Waiting for workers to finish...")
    while not async_result.ready():
        time.sleep(poll_interval)
        print("      ...still processing")

    final = async_result.get()
    print(f"[3/3] Done. Combined JSON written to: {final['output_path']}")
    return final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.main <path_to_pdf>")
        sys.exit(1)
    run(sys.argv[1])
