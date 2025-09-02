#!/usr/bin/env python3
"""
LOKI PDF Indexer - Optimized PDF processing with selective OCR
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Any, Tuple, Optional

# Third-party imports
import numpy as np
import PyPDF2
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("/home/mike/LOKI/logs", "pdf_indexing.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("loki_indexer")

class PDFProcessor:
    """Process PDFs, extract text, and apply OCR when needed"""
    
    def __init__(self, 
                 ocr_enabled: bool = True,
                 ocr_language: str = 'eng',
                 dpi: int = 200,
                 max_pages_per_file: int = 1000,
                 chunk_size: int = 2000,
                 chunk_overlap: int = 200,
                 min_chars_per_page: int = 50):
        """
        Initialize the PDF processor
        
        Args:
            ocr_enabled: Whether to enable OCR for scanned documents
            ocr_language: Language for OCR processing
            dpi: DPI for image conversion (lower for faster processing)
            max_pages_per_file: Maximum number of pages to process per file
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
            min_chars_per_page: Minimum average characters per page before falling back to OCR
        """
        self.ocr_enabled = ocr_enabled
        self.ocr_language = ocr_language
        self.dpi = dpi
        self.max_pages_per_file = max_pages_per_file
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chars_per_page = min_chars_per_page
        
        # Keep track of processed files
        self.processed_files_count = 0
        self.ocr_used_count = 0
        
        # Test if tesseract is installed
        if self.ocr_enabled:
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR is available.")
            except Exception as e:
                logger.error(f"Tesseract OCR is not available: {str(e)}")
                logger.error("OCR functionality will be disabled.")
                self.ocr_enabled = False
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[List[str], bool]:
        """
        Extract text from a PDF file, using OCR only if necessary
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (list of page texts, whether OCR was used)
        """
        logger.info(f"Processing: {pdf_path}")
        
        # Try regular text extraction first
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Check if there are too many pages
                if len(reader.pages) > self.max_pages_per_file:
                    logger.warning(f"PDF has {len(reader.pages)} pages, which exceeds the limit of {self.max_pages_per_file}")
                    logger.warning(f"Processing only the first {self.max_pages_per_file} pages")
                
                # Limit the number of pages to process
                num_pages = min(len(reader.pages), self.max_pages_per_file)
                
                # Extract text from each page
                page_texts = []
                total_text_length = 0
                
                for i in tqdm(range(num_pages), desc="Extracting text", leave=False):
                    try:
                        page = reader.pages[i]
                        text = page.extract_text() or ""
                        total_text_length += len(text)
                        page_texts.append(text)
                    except Exception as e:
                        logger.error(f"Error extracting text from page {i}: {str(e)}")
                        page_texts.append("")
                
                # If we got a reasonable amount of text, return it
                # Otherwise, fall back to OCR if enabled
                avg_chars_per_page = total_text_length / max(1, num_pages)
                logger.info(f"Extracted {total_text_length} characters ({avg_chars_per_page:.1f} chars/page)")
                
                if avg_chars_per_page >= self.min_chars_per_page:
                    return page_texts, False
                else:
                    logger.warning(f"Text extraction yielded only {avg_chars_per_page:.1f} chars/page")
                    if not self.ocr_enabled:
                        logger.warning("OCR is disabled, using text extraction results despite low character count")
                        return page_texts, False
                    logger.warning("Falling back to OCR...")
        except Exception as e:
            logger.error(f"Error during text extraction: {str(e)}")
            if not self.ocr_enabled:
                return [f"TEXT EXTRACTION FAILED: {str(e)}"], False
            logger.warning("Falling back to OCR...")
        
        # If we reach here and OCR is enabled, try OCR
        if self.ocr_enabled:
            try:
                self.ocr_used_count += 1
                return self._extract_text_with_ocr(pdf_path), True
            except Exception as e:
                logger.error(f"OCR processing failed: {str(e)}")
                return [f"OCR FAILED: {str(e)}"], False
        else:
            logger.error("OCR is disabled and text extraction failed")
            return ["TEXT EXTRACTION FAILED AND OCR IS DISABLED"], False
    
    def _extract_text_with_ocr(self, pdf_path: str) -> List[str]:
        """
        Extract text using OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of page texts
        """
        logger.info(f"Using OCR to process: {pdf_path}")
        
        # Convert PDF pages to images
        try:
            # Use lower DPI for faster processing
            logger.info(f"Converting PDF to images with DPI={self.dpi}")
            
            # For large PDFs, we'll process in batches to avoid memory issues
            batch_size = 20  # Process 20 pages at a time
            total_pages = min(self.max_pages_per_file, self._count_pdf_pages(pdf_path))
            page_texts = [""] * total_pages
            
            for batch_start in range(0, total_pages, batch_size):
                batch_end = min(batch_start + batch_size, total_pages)
                logger.info(f"Processing pages {batch_start+1}-{batch_end} of {total_pages}")
                
                images = convert_from_path(
                    pdf_path, 
                    dpi=self.dpi,
                    first_page=batch_start+1,
                    last_page=batch_end,
                    paths_only=False
                )
                
                # Process each image with OCR
                for i, img in enumerate(tqdm(images, desc="OCR Processing", leave=False)):
                    try:
                        # Apply OCR
                        text = pytesseract.image_to_string(img, lang=self.ocr_language)
                        page_texts[batch_start + i] = text
                    except Exception as e:
                        logger.error(f"OCR failed for page {batch_start+i+1}: {str(e)}")
                        page_texts[batch_start + i] = ""
                
                # Force garbage collection
                images = None
            
            return page_texts
            
        except Exception as e:
            logger.error(f"Error in OCR processing: {str(e)}")
            raise
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        """Count the number of pages in a PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except Exception as e:
            logger.error(f"Error counting PDF pages: {str(e)}")
            return 0
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata
        
        Args:
            text: Text to chunk
            metadata: Metadata to include with each chunk
            
        Returns:
            List of dictionaries containing chunks and metadata
        """
        # If text is too short, return as a single chunk
        if len(text) <= self.chunk_size:
            return [{
                "text": text,
                "metadata": metadata,
                "chunk_id": 0
            }]
        
        chunks = []
        chunk_id = 0
        
        # Split by paragraphs first to preserve context
        paragraphs = text.split("\n\n")
        current_chunk = ""
        
        for para in paragraphs:
            # If paragraph is too big, split it into smaller pieces
            if len(para) > self.chunk_size:
                # First add any existing content as a chunk
                if current_chunk:
                    chunks.append({
                        "text": current_chunk,
                        "metadata": metadata,
                        "chunk_id": chunk_id
                    })
                    chunk_id += 1
                    current_chunk = ""
                
                # Then split the paragraph by sentences
                sentences = [s.strip() + "." for s in para.split(".") if s.strip()]
                
                if not sentences:  # If no sentences, just use the paragraph
                    sentences = [para]
                
                current_sentence_chunk = ""
                for sentence in sentences:
                    if len(current_sentence_chunk) + len(sentence) + 1 > self.chunk_size and current_sentence_chunk:
                        # Add the current sentence chunk
                        chunks.append({
                            "text": current_sentence_chunk,
                            "metadata": metadata,
                            "chunk_id": chunk_id
                        })
                        chunk_id += 1
                        # Start a new chunk with overlap
                        current_sentence_chunk = sentence
                    else:
                        # Add sentence to current chunk
                        if current_sentence_chunk:
                            current_sentence_chunk += " " + sentence
                        else:
                            current_sentence_chunk = sentence
                
                # Add any remaining sentence chunk
                if current_sentence_chunk:
                    current_chunk = current_sentence_chunk
                
            # Otherwise check if adding this paragraph would exceed chunk size
            elif len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                # Add the chunk with metadata
                chunks.append({
                    "text": current_chunk,
                    "metadata": metadata,
                    "chunk_id": chunk_id
                })
                
                # Start new chunk with overlap
                if len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
                    
                chunk_id += 1
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add the final chunk if there's anything left
        if current_chunk:
            chunks.append({
                "text": current_chunk,
                "metadata": metadata,
                "chunk_id": chunk_id
            })
        
        # If we're creating too many chunks, combine smaller ones
        max_chunks = 100  # Reasonable maximum number of chunks per document
        if len(chunks) > max_chunks:
            logger.warning(f"Created {len(chunks)} chunks, which is excessive. Consolidating...")
            consolidated_chunks = []
            temp_chunk = {"text": "", "metadata": metadata, "chunk_id": 0}
            
            for i, chunk in enumerate(chunks):
                if len(temp_chunk["text"]) + len(chunk["text"]) < self.chunk_size * 2:
                    # Combine chunks
                    if temp_chunk["text"]:
                        temp_chunk["text"] += "\n\n" + chunk["text"]
                    else:
                        temp_chunk["text"] = chunk["text"]
                else:
                    # Save the current temp chunk and start a new one
                    consolidated_chunks.append(temp_chunk)
                    temp_chunk = {
                        "text": chunk["text"], 
                        "metadata": metadata, 
                        "chunk_id": len(consolidated_chunks)
                    }
            
            # Add the final temp chunk if it has content
            if temp_chunk["text"]:
                consolidated_chunks.append(temp_chunk)
            
            logger.info(f"Consolidated down to {len(consolidated_chunks)} chunks")
            chunks = consolidated_chunks
        
        return chunks

    def process_pdf(self, pdf_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Process a PDF file and save the chunks
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save the chunks
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        output_file = None
        
        try:
            # Generate output filename
            file_name = os.path.basename(pdf_path)
            rel_path = os.path.relpath(pdf_path, "/home/mike/LOKI/DATABASE/survivorlibrary")
            category = os.path.dirname(rel_path).replace("\\", "/")
            
            # Create an output filename based on a hash of the relative path
            # This ensures unique filenames even for files with the same name
            path_hash = hashlib.md5(rel_path.encode()).hexdigest()[:8]
            sanitized_name = "".join(c if c.isalnum() else "_" for c in file_name.rsplit(".", 1)[0])
            output_file = os.path.join(
                output_dir,
                f"{sanitized_name}_{path_hash}.json"
            )
            
            # Check if this file has already been processed
            if os.path.exists(output_file):
                logger.info(f"Skipping already processed file: {pdf_path}")
                self.processed_files_count += 1
                return {
                    "file_name": file_name,
                    "file_path": pdf_path,
                    "status": "skipped",
                    "output_file": output_file
                }
            
            # Extract basic metadata
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # Size in MB
            
            # Extract text (with OCR if needed)
            page_texts, ocr_used = self.extract_text_from_pdf(pdf_path)
            
            # Calculate total text length
            total_text = "\n\n".join(page_texts)
            text_length = len(total_text)
            
            # Prepare metadata
            metadata = {
                "file_name": file_name,
                "file_path": pdf_path,
                "relative_path": rel_path,
                "category": category,
                "file_size_mb": round(file_size, 2),
                "page_count": len(page_texts),
                "ocr_used": ocr_used,
                "processed_date": datetime.now().isoformat(),
            }
            
            # Create chunks
            chunks = self.chunk_text(total_text, metadata)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Save chunks to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": metadata,
                    "chunks": chunks
                }, f, indent=2)
            
            # Return summary
            self.processed_files_count += 1
            processing_time = time.time() - start_time
            return {
                "file_name": file_name,
                "file_path": pdf_path,
                "chunks_created": len(chunks),
                "text_length": text_length,
                "ocr_used": ocr_used,
                "processing_time": round(processing_time, 2),
                "output_file": output_file,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Increment counter even for failed files
            self.processed_files_count += 1
            
            return {
                "file_name": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "error": str(e),
                "status": "failed",
                "output_file": output_file
            }
    
    def find_pdf_files(self, directory: str) -> List[str]:
        """
        Find all PDF files in a directory and its subdirectories
        
        Args:
            directory: Directory to search
            
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        
        logger.info(f"Searching for PDF files in: {directory}")
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        return pdf_files

    def get_completion_status(self) -> Dict[str, Any]:
        """Return statistics about the processing job"""
        return {
            "processed_files": self.processed_files_count,
            "ocr_used": self.ocr_used_count
        }


def main():
    """Main entry point for the PDF indexer"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LOKI PDF Indexer')
    parser.add_argument('--input', type=str, default='/home/mike/LOKI/DATABASE/survivorlibrary',
                        help='Input directory containing PDFs')
    parser.add_argument('--output', type=str, default='/home/mike/LOKI/indexed_data',
                        help='Output directory for indexed data')
    parser.add_argument('--ocr', action='store_true', help='Enable OCR for scanned documents')
    parser.add_argument('--dpi', type=int, default=200,
                        help='DPI for OCR image conversion (lower is faster)')
    parser.add_argument('--max-pages', type=int, default=2000, 
                        help='Maximum pages to process per file')
    parser.add_argument('--chunk-size', type=int, default=2000,
                        help='Maximum characters per chunk')
    parser.add_argument('--chunk-overlap', type=int, default=200,
                        help='Overlap between chunks in characters')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of worker processes')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only 5 files')
    parser.add_argument('--resume', action='store_true',
                        help='Resume processing, skip already indexed files')
    parser.add_argument('--min-chars-per-page', type=int, default=50,
                        help='Minimum average characters per page before using OCR')
    
    args = parser.parse_args()
    
    # Display startup information
    logger.info("=" * 80)
    logger.info(f"LOKI PDF Indexer starting at {datetime.now().isoformat()}")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"OCR enabled: {args.ocr}")
    logger.info(f"DPI for OCR: {args.dpi}")
    logger.info(f"Max pages per file: {args.max_pages}")
    logger.info(f"Chunk size: {args.chunk_size}")
    logger.info(f"Chunk overlap: {args.chunk_overlap}")
    logger.info(f"Min chars per page: {args.min_chars_per_page}")
    logger.info(f"Worker processes: {args.workers}")
    logger.info(f"Test mode: {args.test}")
    logger.info(f"Resume mode: {args.resume}")
    logger.info("=" * 80)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize the processor
    processor = PDFProcessor(
        ocr_enabled=args.ocr,
        dpi=args.dpi,
        max_pages_per_file=args.max_pages,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chars_per_page=args.min_chars_per_page
    )
    
    # Find all PDF files
    pdf_files = processor.find_pdf_files(args.input)
    
    # In test mode, limit to 5 files
    if args.test:
        logger.info("Test mode: limiting to 5 files")
        pdf_files = pdf_files[:5]
    
    # If resuming, identify already processed files
    processed_files = set()
    if args.resume:
        # Scan output directory for existing files
        for root, _, files in os.walk(args.output):
            for file in files:
                if file.endswith('.json'):
                    processed_files.add(file)
        
        logger.info(f"Resume mode: found {len(processed_files)} already processed files")
    
    # Process files
    results = []
    start_time = time.time()
    
    try:
        if args.workers > 1:
            # Process files in parallel
            with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
                # Submit all jobs
                future_to_pdf = {
                    executor.submit(processor.process_pdf, pdf_file, args.output): pdf_file
                    for pdf_file in pdf_files
                }
                
                # Collect results as they complete
                for future in tqdm(concurrent.futures.as_completed(future_to_pdf), 
                                total=len(pdf_files),
                                desc="Processing PDFs"):
                    pdf_file = future_to_pdf[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # Log progress periodically
                        if len(results) % 10 == 0:
                            elapsed = time.time() - start_time
                            files_per_hour = (len(results) / elapsed) * 3600
                            logger.info(f"Processed {len(results)}/{len(pdf_files)} files. "
                                      f"Rate: {files_per_hour:.1f} files/hour. "
                                      f"Estimated completion: {len(pdf_files) / files_per_hour:.1f} hours.")
                    except Exception as e:
                        logger.error(f"Error processing {pdf_file}: {str(e)}")
        else:
            # Process files sequentially
            for i, pdf_file in enumerate(tqdm(pdf_files, desc="Processing PDFs")):
                try:
                    result = processor.process_pdf(pdf_file, args.output)
                    results.append(result)
                    
                    # Log progress periodically
                    if (i+1) % 10 == 0:
                        elapsed = time.time() - start_time
                        files_per_hour = ((i+1) / elapsed) * 3600
                        remaining_hours = (len(pdf_files) - (i+1)) / files_per_hour
                        logger.info(f"Processed {i+1}/{len(pdf_files)} files. "
                                  f"Rate: {files_per_hour:.1f} files/hour. "
                                  f"Estimated completion: {remaining_hours:.1f} hours.")
                except Exception as e:
                    logger.error(f"Error processing {pdf_file}: {str(e)}")
                    
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
    
    # Write summary
    summary_file = os.path.join(args.output, "indexing_summary.json")
    completion_status = processor.get_completion_status()
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "start_time": datetime.now().isoformat(),
            "total_files_found": len(pdf_files),
            "files_processed": completion_status["processed_files"],
            "ocr_used_count": completion_status["ocr_used"],
            "successful_files": sum(1 for r in results if r.get("status") == "success"),
            "failed_files": sum(1 for r in results if r.get("status") == "failed"),
            "skipped_files": sum(1 for r in results if r.get("status") == "skipped"),
            "results": results
        }, f, indent=2)
    
    # Calculate statistics
    successful_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = sum(1 for r in results if r.get("status") == "failed")
    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    ocr_count = sum(1 for r in results if r.get("ocr_used"))
    
    logger.info(f"Processing complete. Summary saved to {summary_file}")
    logger.info(f"Processed: {len(results)} files")
    logger.info(f"Successful: {successful_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"OCR used: {ocr_count} files")


if __name__ == "__main__":
    main()
