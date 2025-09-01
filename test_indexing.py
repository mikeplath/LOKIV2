#!/usr/bin/env python3
"""
LOKI Indexing Test Script - Check if indexed data exists and is valid
"""

import os
import sys
import json
import glob
from datetime import datetime

# Define paths
indexed_data_dir = "/home/mike/LOKI/indexed_data"
database_dir = "/home/mike/LOKI/DATABASE/survivorlibrary"

# Print header
print("=" * 60)
print(f"LOKI Indexing Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Check if indexed data directory exists
if not os.path.exists(indexed_data_dir):
    print(f"ERROR: Indexed data directory not found at: {indexed_data_dir}")
    print("The indexing process has not been started or has not created any output.")
    print("Please run the indexing script first.")
    sys.exit(1)

# Count JSON files in the indexed data directory
json_files = glob.glob(os.path.join(indexed_data_dir, "**", "*.json"), recursive=True)
print(f"Found {len(json_files)} indexed files")

# Count PDF files in the database
pdf_files = []
for root, dirs, files in os.walk(database_dir):
    for file in files:
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(root, file))

print(f"Total PDFs in database: {len(pdf_files)}")

if len(pdf_files) > 0:
    percentage = (len(json_files) / len(pdf_files)) * 100
    print(f"Indexing progress: {percentage:.2f}%")

# Check summary file
summary_file = os.path.join(indexed_data_dir, "indexing_summary.json")
if os.path.exists(summary_file):
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        print("\nSummary Information:")
        print(f"- Start time: {summary.get('start_time', 'Unknown')}")
        print(f"- Total files found: {summary.get('total_files_found', 0)}")
        print(f"- Files processed: {summary.get('files_processed', 0)}")
        print(f"- Successful files: {summary.get('successful_files', 0)}")
        print(f"- Failed files: {summary.get('failed_files', 0)}")
        print(f"- OCR used: {summary.get('ocr_used_count', 0)} files")
    except Exception as e:
        print(f"\nError reading summary file: {e}")
else:
    print("\nNo indexing summary file found.")

# Examine a random indexed file for content
if json_files:
    print("\nExamining a random indexed file...")
    import random
    sample_file = random.choice(json_files)
    print(f"Selected file: {os.path.basename(sample_file)}")
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Show metadata
        if "metadata" in data:
            metadata = data["metadata"]
            print("\nMetadata:")
            print(f"- File name: {metadata.get('file_name', 'Unknown')}")
            print(f"- File path: {metadata.get('file_path', 'Unknown')}")
            print(f"- Category: {metadata.get('category', 'Unknown')}")
            print(f"- Page count: {metadata.get('page_count', 0)}")
            print(f"- OCR used: {metadata.get('ocr_used', False)}")
        
        # Show chunks info
        if "chunks" in data:
            chunks = data["chunks"]
            print(f"\nChunks: {len(chunks)}")
            
            if chunks:
                # Show a sample of the first chunk
                first_chunk = chunks[0]
                text = first_chunk.get("text", "")
                print("\nSample text from first chunk:")
                print("-" * 40)
                # Print first 300 characters
                print(f"{text[:300]}..." if len(text) > 300 else text)
                print("-" * 40)
    except Exception as e:
        print(f"Error examining file: {e}")

print("\nTest complete. If you see sample text above, your indexing is working.")
print("If no sample text is shown or there are errors, your indexing may not be working correctly.")
