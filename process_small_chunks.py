"""
Process book.pdf with smaller chunks (2 pages each instead of 20)
"""
from run_standalone import split_pdf_into_chunks, process_chunk, merge_results
import json
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Process book.pdf with 2-page chunks instead of 20
print('📚 Processing book.pdf with 2-page chunks\n')

manifest = split_pdf_into_chunks('input/book.pdf', chunk_size=2)

print(f'[1/3] Split into {manifest["num_chunks"]} chunks ({manifest["total_pages"]} pages)')
print()

# Process each chunk
chunk_results = []
print('[2/3] Processing chunks...')
for chunk_meta in manifest['chunks']:
    chunk_id = chunk_meta['chunk_id']
    print(f'  Chunk {chunk_id}: Pages {chunk_meta["start_page"]}-{chunk_meta["end_page"]}...', end='', flush=True)
    result = process_chunk(chunk_meta)
    chunk_results.append(result)
    print(' ✓')

# Merge
print('[3/3] Merging results...')
output_path = merge_results(chunk_results, 'input/book.pdf')
print(f'  ✓ Written to: {output_path}')
print()

# Show summary
with open(output_path) as f:
    merged = json.load(f)

print('=== RESULT ===')
print(f'Total Pages: {merged["total_pages"]}')
print(f'Total Words: {merged["total_word_count"]:,}')
print(f'Chunks: {merged["num_chunks"]}')
print()
print('Chunk Breakdown:')
for chunk in merged['chunks']:
    print(f'  Chunk {chunk["chunk_id"]}: Pages {chunk["start_page"]}-{chunk["end_page"]} ({chunk["page_count"]} pages) - {chunk["word_count"]} words')
