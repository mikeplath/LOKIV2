#!/usr/bin/env python3
"""
LOKI Vector Database Creator - Convert indexed text into searchable vectors
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import faiss
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("/home/mike/LOKI/logs", "vector_db.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("loki_vector_db")

class VectorDatabaseCreator:
    """Create a vector database from indexed text chunks"""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 batch_size: int = 32,
                 max_seq_length: int = 512,
                 vector_size: int = 384,
                 index_type: str = "Flat"):
        """
        Initialize the vector database creator
        
        Args:
            model_name: Name of the sentence transformer model to use
            batch_size: Number of chunks to encode at once
            max_seq_length: Maximum sequence length for the model
            vector_size: Size of the vectors (depends on the model)
            index_type: Type of FAISS index to use
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.vector_size = vector_size
        self.index_type = index_type
        
        # Initialize the model
        logger.info(f"Loading sentence transformer model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.model.max_seq_length = max_seq_length
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def create_vector_db(self, indexed_data_dir: str, output_dir: str, skip_empty: bool = True) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Create a vector database from indexed text chunks
        
        Args:
            indexed_data_dir: Directory containing indexed JSON files
            output_dir: Directory to save the vector database
            skip_empty: Whether to skip chunks with empty text
            
        Returns:
            Tuple of (FAISS index, list of metadata)
        """
        # Find all JSON files
        logger.info(f"Searching for indexed files in: {indexed_data_dir}")
        json_files = []
        for root, _, files in os.walk(indexed_data_dir):
            for file in files:
                if file.endswith('.json') and file != "indexing_summary.json":
                    json_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(json_files)} indexed files")
        
        # Initialize vectors and metadata
        all_metadata = []
        all_texts = []
        empty_chunks = 0
        total_chunks = 0
        
        # Process each JSON file
        for json_file in tqdm(json_files, desc="Reading indexed files"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract chunks
                if "chunks" in data:
                    for chunk in data["chunks"]:
                        if "text" in chunk and "metadata" in chunk:
                            text = chunk["text"]
                            metadata = chunk["metadata"].copy()  # Make a copy to avoid modifying the original
                            
                            # Add chunk ID to metadata
                            metadata["chunk_id"] = chunk.get("chunk_id", 0)
                            
                            # Add vector_id (position in the array)
                            metadata["vector_id"] = len(all_texts)
                            
                            # Skip if text is empty and skip_empty is True
                            if not text and skip_empty:
                                empty_chunks += 1
                                continue
                                
                            all_texts.append(text)
                            all_metadata.append(metadata)
                            total_chunks += 1
            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")
        
        if empty_chunks > 0:
            logger.warning(f"Skipped {empty_chunks} empty chunks")
        
        logger.info(f"Loaded {len(all_texts)} text chunks for encoding")
        
        if not all_texts:
            logger.error("No text chunks found. Cannot create vector database.")
            return None, []
        
        # Create FAISS index
        logger.info(f"Creating {self.index_type} index with dimension {self.vector_size}")
        
        if self.index_type == "Flat":
            index = faiss.IndexFlatIP(self.vector_size)
        elif self.index_type == "IVF":
            quantizer = faiss.IndexFlatIP(self.vector_size)
            nlist = min(4096, 8 * round(len(all_texts) / 10))  # Rule of thumb
            index = faiss.IndexIVFFlat(quantizer, self.vector_size, nlist)
            index.nprobe = 64  # Number of clusters to visit during search
        else:
            logger.error(f"Unknown index type: {self.index_type}")
            raise ValueError(f"Unknown index type: {self.index_type}")
        
        # Check for empty index
        if len(all_texts) == 0:
            logger.error("No texts to encode. Cannot create vector database.")
            return None, []
        
        # Encode vectors in batches
        logger.info(f"Encoding {len(all_texts)} texts in batches of {self.batch_size}")
        
        all_vectors = []
        for i in tqdm(range(0, len(all_texts), self.batch_size), desc="Encoding vectors"):
            batch_texts = all_texts[i:i+self.batch_size]
            
            try:
                batch_vectors = self.model.encode(batch_texts, show_progress_bar=False)
                all_vectors.append(batch_vectors)
            except Exception as e:
                logger.error(f"Error encoding batch {i//self.batch_size}: {str(e)}")
                logger.error(traceback.format_exc())
                # Try encoding one by one to identify problematic texts
                for j, text in enumerate(batch_texts):
                    try:
                        vector = self.model.encode([text], show_progress_bar=False)
                        all_vectors.append(vector)
                    except Exception as e:
                        logger.error(f"Error encoding text at position {i+j}: {str(e)}")
                        # Add a zero vector as placeholder
                        all_vectors.append(np.zeros((1, self.vector_size)))
        
        # Concatenate vectors
        try:
            if all_vectors:
                vectors = np.vstack(all_vectors)
                
                # Normalize vectors for cosine similarity
                faiss.normalize_L2(vectors)
                
                # Add vectors to index
                logger.info(f"Adding {len(vectors)} vectors to index")
                index.add(vectors)
                
                # Create directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # Save the index
                index_file = os.path.join(output_dir, "faiss_index.bin")
                logger.info(f"Saving index to: {index_file}")
                faiss.write_index(index, index_file)
                
                # Save the metadata
                metadata_file = os.path.join(output_dir, "metadata.json")
                logger.info(f"Saving metadata to: {metadata_file}")
                
                # We need to make metadata JSON serializable
                serializable_metadata = []
                for item in all_metadata:
                    # Convert any non-serializable items to strings
                    serializable_item = {}
                    for k, v in item.items():
                        if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                            serializable_item[k] = v
                        else:
                            serializable_item[k] = str(v)
                    serializable_metadata.append(serializable_item)
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(serializable_metadata, f)
                
                logger.info("Vector database created successfully")
                
                # Return the index and metadata
                return index, serializable_metadata
            else:
                logger.error("No vectors were created. Cannot save index.")
                return None, []
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
            logger.error(traceback.format_exc())
            return None, []
    
    def test_search(self, index, metadata: List[Dict[str, Any]], query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Test search functionality
        
        Args:
            index: FAISS index
            metadata: List of metadata for each vector
            query: Query string
            k: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            # Encode the query
            query_vector = self.model.encode([query])[0].reshape(1, -1)
            
            # Normalize the query vector
            faiss.normalize_L2(query_vector)
            
            # Search the index
            distances, indices = index.search(query_vector, k)
            
            # Format results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(metadata):  # Check if index is valid
                    result = {
                        "score": float(distances[0][i]),
                        "metadata": metadata[idx],
                        "vector_id": idx
                    }
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

def main():
    """Main entry point for the vector database creator"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LOKI Vector Database Creator')
    parser.add_argument('--input', type=str, default='/home/mike/LOKI/indexed_data',
                        help='Input directory containing indexed JSON files')
    parser.add_argument('--output', type=str, default='/home/mike/LOKI/vector_db',
                        help='Output directory for vector database')
    parser.add_argument('--model', type=str, default='all-MiniLM-L6-v2',
                        help='Sentence transformer model to use')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size for encoding')
    parser.add_argument('--test-query', type=str,
                        help='Optional query to test search functionality')
    
    args = parser.parse_args()
    
    # Display startup information
    logger.info("=" * 80)
    logger.info(f"LOKI Vector Database Creator starting at {datetime.now().isoformat()}")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 80)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize the creator
    creator = VectorDatabaseCreator(
        model_name=args.model,
        batch_size=args.batch_size
    )
    
    # Create the vector database
    try:
        index, metadata = creator.create_vector_db(args.input, args.output)
        
        # Test search if a query was provided
        if args.test_query and index is not None:
            logger.info(f"Testing search with query: {args.test_query}")
            results = creator.test_search(index, metadata, args.test_query)
            
            logger.info(f"Found {len(results)} results:")
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}:")
                logger.info(f"  Score: {result['score']:.4f}")
                logger.info(f"  File: {result['metadata'].get('file_name', 'Unknown')}")
                logger.info(f"  Path: {result['metadata'].get('relative_path', 'Unknown')}")
                logger.info(f"  Chunk ID: {result['metadata'].get('chunk_id', 'Unknown')}")
                
                # Show a snippet of the text
                text_file = os.path.join(args.input, os.path.basename(result['metadata'].get('file_path', '')).replace('.pdf', '.json'))
                if os.path.exists(text_file):
                    try:
                        with open(text_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            chunk_id = result['metadata'].get('chunk_id', 0)
                            for chunk in data.get('chunks', []):
                                if chunk.get('chunk_id') == chunk_id:
                                    text = chunk.get('text', '')
                                    # Show the first 200 characters
                                    snippet = text[:200] + "..." if len(text) > 200 else text
                                    logger.info(f"  Text snippet: {snippet}")
                                    break
                    except Exception as e:
                        logger.error(f"Error reading text file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error creating vector database: {str(e)}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
