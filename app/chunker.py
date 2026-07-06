"""
Splits a large PDF into fixed-size page chunks (default: 20 pages each)
so each chunk can be processed independently and in parallel by a worker.
"""
import os
import math
from pypdf import PdfReader, PdfWriter

from app.config import CHUNK_SIZE, OUTPUT_DIR


def split_pdf_into_chunks(pdf_path: str, chunk_size: int = CHUNK_SIZE, out_dir: str = None):
    """
    Splits `pdf_path` into chunk_size-page PDFs.

    Returns a list of dicts:
        [{"chunk_id": 0, "path": "...", "start_page": 1, "end_page": 20}, ...]
    """
    out_dir = out_dir or os.path.join(OUTPUT_DIR, "chunks")
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
            "source_file": pdf_path,
            "start_page": start + 1,   # human-readable, 1-indexed
            "end_page": end,           # inclusive
            "page_count": end - start,
        })

    return {
        "source_file": pdf_path,
        "total_pages": total_pages,
        "chunk_size": chunk_size,
        "num_chunks": num_chunks,
        "chunks": chunks,
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m app.chunker <path_to_pdf>")
        sys.exit(1)

    manifest = split_pdf_into_chunks(sys.argv[1])
    print(json.dumps(manifest, indent=2))
