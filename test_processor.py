"""
Unit tests for the book chunk processor.

Run with: python -m pytest test_processor.py -v
"""
import os
import json
import tempfile
import shutil
from pathlib import Path

import pytest
import pdfplumber
from pypdf import PdfWriter

# Import functions to test
from run_standalone import split_pdf_into_chunks, process_chunk, merge_results


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def sample_pdf(temp_dir):
    """Create a simple test PDF with 5 pages."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    pdf_path = os.path.join(temp_dir, "test.pdf")
    
    # Create a simple PDF with 5 pages
    c = canvas.Canvas(pdf_path, pagesize=letter)
    for page_num in range(5):
        c.drawString(100, 750, f"Test Page {page_num + 1}")
        c.drawString(100, 700, "This is sample text for testing the PDF processor.")
        c.drawString(100, 650, "It contains multiple words to test word counting.")
        c.showPage()
    c.save()
    
    return pdf_path


class TestSplitPDF:
    """Tests for the PDF splitting function."""
    
    def test_split_creates_chunks(self, sample_pdf, temp_dir):
        """Test that PDF is split into correct number of chunks."""
        chunk_size = 2
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=chunk_size)
        
        assert manifest["total_pages"] == 5
        assert manifest["chunk_size"] == chunk_size
        assert manifest["num_chunks"] == 3  # 5 pages / 2 pages per chunk = 3 chunks
        assert len(manifest["chunks"]) == 3
    
    def test_chunk_metadata_correct(self, sample_pdf):
        """Test that chunk metadata is correct."""
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=2)
        chunks = manifest["chunks"]
        
        # First chunk
        assert chunks[0]["chunk_id"] == 0
        assert chunks[0]["start_page"] == 1
        assert chunks[0]["end_page"] == 2
        assert chunks[0]["page_count"] == 2
        
        # Last chunk
        assert chunks[2]["chunk_id"] == 2
        assert chunks[2]["start_page"] == 5
        assert chunks[2]["end_page"] == 5
        assert chunks[2]["page_count"] == 1
    
    def test_chunk_files_created(self, sample_pdf, temp_dir):
        """Test that chunk PDF files are actually created."""
        output_dir = os.path.join(temp_dir, "test_chunks")
        manifest = split_pdf_into_chunks(
            sample_pdf, 
            chunk_size=2,
        )
        
        # Check that chunk files exist
        for chunk in manifest["chunks"]:
            assert os.path.exists(chunk["path"])
            assert chunk["path"].endswith(".pdf")


class TestProcessChunk:
    """Tests for the chunk processing function."""
    
    def test_process_chunk_extracts_text(self, sample_pdf):
        """Test that text is extracted from PDF chunk."""
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=5)
        chunk_meta = manifest["chunks"][0]
        
        result = process_chunk(chunk_meta)
        
        # Check result structure
        assert "chunk_id" in result
        assert "result_path" in result
        assert "status" in result
        assert result["status"] == "done"
    
    def test_process_chunk_output_json(self, sample_pdf):
        """Test that JSON output is valid and contains expected fields."""
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=5)
        chunk_meta = manifest["chunks"][0]
        
        result = process_chunk(chunk_meta)
        
        # Read and verify the JSON output
        with open(result["result_path"], "r") as f:
            chunk_result = json.load(f)
        
        assert "chunk_id" in chunk_result
        assert "word_count" in chunk_result
        assert "char_count" in chunk_result
        assert "pages" in chunk_result
        assert isinstance(chunk_result["pages"], list)
        assert chunk_result["word_count"] > 0


class TestMergeResults:
    """Tests for the merge results function."""
    
    def test_merge_multiple_chunks(self, sample_pdf):
        """Test that multiple chunks are merged correctly."""
        # Process multiple chunks
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=2)
        
        chunk_results = []
        for chunk_meta in manifest["chunks"]:
            result = process_chunk(chunk_meta)
            chunk_results.append(result)
        
        # Merge results
        output_path = merge_results(chunk_results, sample_pdf)
        
        # Verify merged output
        with open(output_path, "r") as f:
            merged = json.load(f)
        
        assert merged["num_chunks"] == 3
        assert len(merged["chunks"]) == 3
        assert "total_pages" in merged
        assert "total_word_count" in merged
    
    def test_merged_word_count_sum(self, sample_pdf):
        """Test that merged word count is sum of individual chunks."""
        manifest = split_pdf_into_chunks(sample_pdf, chunk_size=2)
        
        chunk_results = []
        individual_word_counts = []
        for chunk_meta in manifest["chunks"]:
            result = process_chunk(chunk_meta)
            chunk_results.append(result)
            
            with open(result["result_path"], "r") as f:
                chunk_data = json.load(f)
                individual_word_counts.append(chunk_data["word_count"])
        
        output_path = merge_results(chunk_results, sample_pdf)
        
        with open(output_path, "r") as f:
            merged = json.load(f)
        
        # Total word count should equal sum of individual chunks
        expected_total = sum(individual_word_counts)
        assert merged["total_word_count"] == expected_total


class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_full_pipeline(self, sample_pdf, temp_dir):
        """Test complete pipeline: split -> process -> merge."""
        # Mock the OUTPUT_DIR
        global OUTPUT_DIR
        original_output = OUTPUT_DIR if 'OUTPUT_DIR' in globals() else None
        
        try:
            # Run full pipeline
            manifest = split_pdf_into_chunks(sample_pdf, chunk_size=2)
            
            chunk_results = []
            for chunk_meta in manifest["chunks"]:
                result = process_chunk(chunk_meta)
                chunk_results.append(result)
            
            output_path = merge_results(chunk_results, sample_pdf)
            
            # Verify everything was created
            assert os.path.exists(output_path)
            
            with open(output_path, "r") as f:
                final_result = json.load(f)
            
            # Verify structure
            assert final_result["source_file"] == sample_pdf
            assert final_result["num_chunks"] == 3
            assert final_result["total_pages"] == 5
            assert final_result["total_word_count"] > 0
            
        finally:
            if original_output:
                OUTPUT_DIR = original_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
