"""
Standalone PDF chunk processor — no Redis or Celery required.
This runs synchronously (not parallel) but demonstrates all the functionality.

Usage:
    python run_standalone.py input/book.pdf
"""
import sys
import json
import time
import os
import math

import pdfplumber
from pypdf import PdfReader, PdfWriter

OUTPUT_DIR = "output"
CHUNK_SIZE = 2


def split_pdf_into_chunks(pdf_path: str, chunk_size: int = CHUNK_SIZE):
    """Split PDF into chunks."""
    out_dir = os.path.join(OUTPUT_DIR, "chunks")
    os.makedirs(out_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    num_chunks = math.ceil(total_pages / chunk_size)

    chunks = []
    for chunk_id in range(num_chunks):
        start = chunk_id * chunk_size
        end = min(start + chunk_size, total_pages)

        writer = PdfWriter()
        for page_index in range(start, end):
            writer.add_page(reader.pages[page_index])

        chunk_path = os.path.join(out_dir, f"chunk_{chunk_id:04d}.pdf")
        with open(chunk_path, "wb") as f:
            writer.write(f)

        chunks.append({
            "chunk_id": chunk_id,
            "path": chunk_path,
            "start_page": start + 1,
            "end_page": end,
            "page_count": end - start,
            "source_file": pdf_path,
        })

    return {
        "source_file": pdf_path,
        "total_pages": total_pages,
        "chunk_size": chunk_size,
        "num_chunks": num_chunks,
        "chunks": chunks,
    }


def process_chunk(chunk_meta: dict):
    """Process one chunk (standalone, no Celery)."""
    chunk_id = chunk_meta["chunk_id"]
    chunk_path = chunk_meta["path"]

    print(f"  Processing chunk {chunk_id}...", end="", flush=True)

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
        "chunk_path": chunk_path,
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

    print(" ✓")
    return {"chunk_id": chunk_id, "result_path": result_path, "status": "done"}


def merge_results(chunk_results: list, source_file: str):
    """Merge all chunk results into one file."""
    print("[3/3] Merging results...")

    merged = {
        "source_file": source_file,
        "num_chunks": len(chunk_results),
        "chunks": [],
    }

    ordered = sorted(chunk_results, key=lambda r: r["chunk_id"])
    for r in ordered:
        with open(r["result_path"], "r", encoding="utf-8") as f:
            merged["chunks"].append(json.load(f))

    merged["total_pages"] = sum(c["page_count"] for c in merged["chunks"])
    merged["total_word_count"] = sum(c["word_count"] for c in merged["chunks"])

    out_path = os.path.join(OUTPUT_DIR, "book_full.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return out_path


def main(pdf_path: str):
    """Main orchestration."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        sys.exit(1)

    print(f"\n📚 Book Chunk Processor (Standalone)\n")
    
    # Step 1: Split
    print(f"[1/3] Splitting {pdf_path} into chunks...")
    manifest = split_pdf_into_chunks(pdf_path)
    print(f"      ✓ {manifest['num_chunks']} chunks ({manifest['total_pages']} pages, "
          f"{manifest['chunk_size']} pages/chunk)")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Step 2: Process chunks (sequentially in this standalone version)
    print("[2/3] Processing chunks...")
    chunk_results = []
    for chunk_meta in manifest["chunks"]:
        result = process_chunk(chunk_meta)
        chunk_results.append(result)

    # Step 3: Merge
    output_path = merge_results(chunk_results, pdf_path)
    
    print(f"      ✓ Merged JSON written to: {output_path}\n")
    
    # Show summary
    with open(output_path, "r") as f:
        final = json.load(f)
    
    print(f"📊 Summary:")
    print(f"   Total pages:  {final['total_pages']}")
    print(f"   Total words:  {final['total_word_count']:,}")
    print(f"   Chunks:       {final['num_chunks']}")
    print(f"   Output files: {OUTPUT_DIR}/")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        pdf_path = "input/book.pdf"
    else:
        pdf_path = sys.argv[1]

    main(pdf_path)
