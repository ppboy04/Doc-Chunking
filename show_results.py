import json

# Show merged result summary
with open('output/book_full.json') as f:
    merged = json.load(f)

print('=== MERGED RESULT ===')
print(f'Total Pages: {merged["total_pages"]}')
print(f'Total Word Count: {merged["total_word_count"]:,}')
print(f'Chunks: {merged["num_chunks"]}')
print()

# Show individual chunk stats
print('=== CHUNK STATS ===')
for chunk in merged['chunks']:
    print(f'Chunk {chunk["chunk_id"]:02d}: Pages {chunk["start_page"]:3d}-{chunk["end_page"]:3d} | {chunk["word_count"]:6,} words | {chunk["char_count"]:7,} chars')
