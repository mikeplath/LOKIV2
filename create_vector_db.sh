#!/bin/bash

# LOKI Vector Database Creation Script - OPTIMIZED FOR SPEED
# This script creates a vector database from indexed data

# Create timestamps and directories
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="/home/mike/LOKI/logs/vector_db_creation_$TIMESTAMP.log"
PROGRESS_FILE="/home/mike/LOKI/logs/vector_db_progress.txt"

# Make sure directories exist
mkdir -p /home/mike/LOKI/logs
mkdir -p /home/mike/LOKI/vector_db

# Function to disable screen blanking
disable_screen_blanking() {
    echo "Disabling screen blanking and power saving..." | tee -a "$LOG_FILE"
    gsettings set org.gnome.desktop.session idle-delay 0
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
    
    echo "Screen blanking disabled." | tee -a "$LOG_FILE"
    echo "Current idle-delay value: $(gsettings get org.gnome.desktop.session idle-delay)" | tee -a "$LOG_FILE"
    echo "Current power setting: $(gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type)" | tee -a "$LOG_FILE"
}

# Function to restore screen blanking
restore_screen_blanking() {
    echo "Restoring default power settings..." | tee -a "$LOG_FILE"
    gsettings set org.gnome.desktop.session idle-delay 300
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
    echo "Power settings restored." | tee -a "$LOG_FILE"
}

# Function to monitor system resources
monitor_system() {
    SYSTEM_LOG="/home/mike/LOKI/logs/system_monitor_$TIMESTAMP.log"
    echo "System Monitoring Started at $(date)" > "$SYSTEM_LOG"
    echo "------------------------------------" >> "$SYSTEM_LOG"
    
    while true; do
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
        MEM_USED=$(free -m | awk 'NR==2{print $3}')
        MEM_PERCENTAGE=$(echo "scale=1; $MEM_USED*100/$MEM_TOTAL" | bc)
        
        echo "$(date +'%Y-%m-%d %H:%M:%S') - CPU: ${CPU_USAGE}% | RAM: ${MEM_USED}MB/${MEM_TOTAL}MB (${MEM_PERCENTAGE}%)" >> "$SYSTEM_LOG"
        sleep 60
    done
}

# Function to monitor progress
monitor_progress() {
    echo "Vector Database Creation Progress" > "$PROGRESS_FILE"
    echo "Started at $(date)" >> "$PROGRESS_FILE"
    echo "----------------------------" >> "$PROGRESS_FILE"
    
    while true; do
        if [ -f "/home/mike/LOKI/vector_db/db_info.json" ]; then
            echo "Process complete!" > "$PROGRESS_FILE"
            echo "Finished at $(date)" >> "$PROGRESS_FILE"
            break
        fi
        
        # Check if embedding process has started
        EMBEDDING_COUNT=$(grep -c "Generating embeddings" "$LOG_FILE" 2>/dev/null)
        if [ "$EMBEDDING_COUNT" -gt 0 ]; then
            # Extract progress from log file
            CURRENT_BATCH=$(grep "Generating embeddings" "$LOG_FILE" | tail -1 | grep -o '[0-9]*/[0-9]*' | cut -d'/' -f1)
            TOTAL_BATCHES=$(grep "Generating embeddings" "$LOG_FILE" | tail -1 | grep -o '[0-9]*/[0-9]*' | cut -d'/' -f2)
            
            if [ -n "$CURRENT_BATCH" ] && [ -n "$TOTAL_BATCHES" ]; then
                PERCENTAGE=$((CURRENT_BATCH * 100 / TOTAL_BATCHES))
                echo "Progress: $PERCENTAGE% ($CURRENT_BATCH/$TOTAL_BATCHES batches)" > "$PROGRESS_FILE"
                echo "Last updated: $(date)" >> "$PROGRESS_FILE"
            else
                echo "Processing data... (progress not available)" > "$PROGRESS_FILE"
                echo "Last updated: $(date)" >> "$PROGRESS_FILE"
            fi
        else
            echo "Preparing data for vector embedding..." > "$PROGRESS_FILE"
            echo "Last updated: $(date)" >> "$PROGRESS_FILE"
        fi
        
        sleep 60  # Update every minute
    done
}

# Display information about the process
echo "===========================================" | tee -a "$LOG_FILE"
echo "LOKI Vector Database Creation - SPEED OPTIMIZED" | tee -a "$LOG_FILE"
echo "Started at $(date)" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"
echo "This process will create a vector database from your indexed data." | tee -a "$LOG_FILE"
echo "This version is optimized for speed rather than maximum accuracy." | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Progress file: $PROGRESS_FILE" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"

# Count JSON files
JSON_COUNT=$(find /home/mike/LOKI/indexed_data -name "*.json" | wc -l)
echo "Found $JSON_COUNT indexed files to process" | tee -a "$LOG_FILE"

# Ask for confirmation
echo "Are you ready to start creating the vector database?"
echo "This is the FASTER version using the smaller model."
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Ask for batch size
echo "Enter batch size for processing (recommended: 64 for your 32GB RAM system):"
read BATCH_SIZE

if ! [[ "$BATCH_SIZE" =~ ^[0-9]+$ ]]; then
    BATCH_SIZE=64
    echo "Invalid input. Using default batch size of 64." | tee -a "$LOG_FILE"
fi
echo "Using batch size of $BATCH_SIZE" | tee -a "$LOG_FILE"

# Ask for test query
echo "Enter a test query to verify the database (e.g., 'water purification'):"
read TEST_QUERY

# Disable screen blanking
disable_screen_blanking

# Start system monitoring in background
monitor_system &
SYSTEM_PID=$!

# Start progress monitoring in background
monitor_progress &
MONITOR_PID=$!

# Create Python script for vector database creation
echo "Creating Python script for vector database creation..." | tee -a "$LOG_FILE"

cat > /home/mike/LOKI/create_vector_db.py << 'PYEOF'
#!/usr/bin/env python3
import os
import json
import glob
import time
import sys
import argparse
from datetime import datetime
from tqdm import tqdm
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle

def load_json_files(directory, max_files=None):
    """Load JSON files from directory recursively."""
    json_files = glob.glob(os.path.join(directory, "**", "*.json"), recursive=True)
    
    if max_files:
        json_files = json_files[:max_files]
    
    return json_files

def extract_chunks_from_files(json_files, batch_size=32):
    """Extract chunks from JSON files."""
    all_chunks = []
    all_metadata = []
    
    for i in tqdm(range(0, len(json_files), batch_size), desc="Loading files"):
        batch_files = json_files[i:i+batch_size]
        
        for file_path in batch_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'chunks' in data and 'metadata' in data:
                    for chunk in data['chunks']:
                        all_chunks.append(chunk['text'])
                        
                        # Add metadata with source information
                        chunk_metadata = {
                            'chunk_id': chunk.get('chunk_id', 'unknown'),
                            'file_name': data['metadata'].get('file_name', os.path.basename(file_path)),
                            'file_path': data['metadata'].get('file_path', file_path),
                            'category': data['metadata'].get('category', 'unknown'),
                            'page_num': chunk.get('page_num', 0)
                        }
                        all_metadata.append(chunk_metadata)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    return all_chunks, all_metadata

def create_vector_database(chunks, metadata, model_name, output_dir, batch_size=32):
    """Create vector database using FAISS."""
    # Load the sentence transformer model
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Get embedding dimension
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"Embedding dimension: {embedding_dim}")
    
    # Create FAISS index
    print("Creating FAISS index")
    index = faiss.IndexFlatL2(embedding_dim)
    
    # Process chunks in batches to generate embeddings
    all_embeddings = []
    total_chunks = len(chunks)
    
    for i in tqdm(range(0, total_chunks, batch_size), desc="Generating embeddings"):
        batch_chunks = chunks[i:i+batch_size]
        batch_embeddings = model.encode(batch_chunks)
        all_embeddings.append(batch_embeddings)
    
    # Concatenate all embeddings
    embeddings = np.vstack(all_embeddings)
    
    # Add embeddings to the index
    index.add(embeddings)
    
    # Save the index, chunks, and metadata
    os.makedirs(output_dir, exist_ok=True)
    
    faiss.write_index(index, os.path.join(output_dir, "faiss_index.bin"))
    
    with open(os.path.join(output_dir, "chunks.pkl"), 'wb') as f:
        pickle.dump(chunks, f)
    
    with open(os.path.join(output_dir, "metadata.pkl"), 'wb') as f:
        pickle.dump(metadata, f)
    
    # Save additional info
    info = {
        "creation_date": datetime.now().isoformat(),
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "num_chunks": total_chunks,
        "num_documents": len(set(m['file_path'] for m in metadata))
    }
    
    with open(os.path.join(output_dir, "db_info.json"), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    
    return index, info

def test_query(query, index, chunks, metadata, model_name, top_k=5):
    """Test a query against the vector database."""
    model = SentenceTransformer(model_name)
    
    # Encode the query
    query_embedding = model.encode([query])[0].reshape(1, -1)
    
    # Search the index
    distances, indices = index.search(query_embedding, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx >= 0 and idx < len(chunks):
            result = {
                "chunk": chunks[idx],
                "metadata": metadata[idx],
                "distance": float(distances[0][i])
            }
            results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Create a vector database from indexed documents")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="Embedding model to use")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for processing")
    parser.add_argument("--test-query", type=str, help="Test query to run against the database")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # Define paths
    indexed_dir = "/home/mike/LOKI/indexed_data"
    output_dir = "/home/mike/LOKI/vector_db"
    
    print(f"Loading indexed files from {indexed_dir}")
    json_files = load_json_files(indexed_dir)
    print(f"Found {len(json_files)} JSON files")
    
    print("Extracting chunks from files")
    chunks, metadata = extract_chunks_from_files(json_files, args.batch_size)
    print(f"Extracted {len(chunks)} chunks")
    
    print(f"Creating vector database using {args.model}")
    index, info = create_vector_database(chunks, metadata, args.model, output_dir, args.batch_size)
    
    print("\nVector database creation complete!")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    print(f"Total chunks: {len(chunks)}")
    print(f"Database saved to: {output_dir}")
    
    # Run test query if provided
    if args.test_query:
        print(f"\nTesting query: '{args.test_query}'")
        results = test_query(args.test_query, index, chunks, metadata, args.model)
        
        print("\nTop 5 results:")
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"Distance: {result['distance']:.4f}")
            print(f"Category: {result['metadata']['category']}")
            print(f"Source: {result['metadata']['file_name']}")
            print(f"Page: {result['metadata']['page_num']}")
            print(f"Text snippet: {result['chunk'][:200]}...")
    
    # Create a status file to indicate successful completion
    with open(os.path.join(output_dir, "status.json"), 'w', encoding='utf-8') as f:
        json.dump({
            "status": "complete",
            "date": datetime.now().isoformat(),
            "info": info
        }, f, indent=2)

if __name__ == "__main__":
    main()
PYEOF

# Run the vector database creation script
echo "Starting vector database creation..." | tee -a "$LOG_FILE"
cd /home/mike/LOKI

# Use the faster model (all-MiniLM-L6-v2) with the specified batch size
python3 create_vector_db.py --model "all-MiniLM-L6-v2" --batch-size $BATCH_SIZE --test-query "$TEST_QUERY" 2>&1 | tee -a "$LOG_FILE"

# Check if the process was successful
if [ -f "/home/mike/LOKI/vector_db/status.json" ]; then
    echo "Vector database creation completed successfully!" | tee -a "$LOG_FILE"
else
    echo "Vector database creation may have failed. Check the log for errors." | tee -a "$LOG_FILE"
fi

# Kill background processes
kill $SYSTEM_PID 2>/dev/null
kill $MONITOR_PID 2>/dev/null

# Restore screen blanking
restore_screen_blanking

echo "===========================================" | tee -a "$LOG_FILE"
echo "Vector Database Creation Finished at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"

# Display instructions for checking progress
echo ""
echo "To check progress while this is running, open a new terminal and type:"
echo "cat /home/mike/LOKI/logs/vector_db_progress.txt"
echo ""
echo "To check system resource usage, open a new terminal and type:"
echo "cat /home/mike/LOKI/logs/system_monitor_*.log | tail -10"
