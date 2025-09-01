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
