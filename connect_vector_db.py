#!/usr/bin/env python3
"""
Connect the Vector Database to the LOKI GUI
"""

import os
import sys
import json
import logging
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import faiss
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("/home/mike/LOKI/logs", "vector_db_connection.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("loki_vector_db_connection")

class VectorDBConnector:
    """Connect to the vector database for searching"""
    
    def __init__(self, 
                 vector_db_dir: str,
                 model_name: str = "all-MiniLM-L6-v2",
                 max_seq_length: int = 512):
        """
        Initialize the vector database connector
        
        Args:
            vector_db_dir: Directory containing the vector database
            model_name: Name of the sentence transformer model to use
            max_seq_length: Maximum sequence length for the model
        """
        self.vector_db_dir = vector_db_dir
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        
        # Load the index
        index_file = os.path.join(vector_db_dir, "faiss_index.bin")
        if not os.path.exists(index_file):
            raise ValueError(f"Index file not found: {index_file}")
        
        logger.info(f"Loading FAISS index from: {index_file}")
        self.index = faiss.read_index(index_file)
        logger.info(f"Index contains {self.index.ntotal} vectors")
        
        # Load the metadata
        metadata_file = os.path.join(vector_db_dir, "metadata.json")
        if not os.path.exists(metadata_file):
            raise ValueError(f"Metadata file not found: {metadata_file}")
        
        logger.info(f"Loading metadata from: {metadata_file}")
        with open(metadata_file, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        logger.info(f"Loaded metadata for {len(self.metadata)} vectors")
        
        # Initialize the model
        logger.info(f"Loading sentence transformer model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.model.max_seq_length = max_seq_length
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the vector database
        
        Args:
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
            distances, indices = self.index.search(query_vector, k)
            
            # Format results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.metadata):  # Check if index is valid
                    result = {
                        "score": float(distances[0][i]),
                        "metadata": self.metadata[idx],
                        "vector_id": int(idx)
                    }
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []
    
    def test_search(self, query: str, k: int = 5) -> None:
        """
        Test search functionality with a query
        
        Args:
            query: Query string
            k: Number of results to return
        """
        results = self.search(query, k)
        
        print(f"\nSearch results for query: '{query}'")
        print("=" * 50)
        
        if not results:
            print("No results found.")
            return
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Score: {result['score']:.4f}")
            print(f"  File: {result['metadata'].get('file_name', 'Unknown')}")
            print(f"  Path: {result['metadata'].get('relative_path', 'Unknown')}")
            
            # Add more metadata as needed
            if 'category' in result['metadata']:
                print(f"  Category: {result['metadata']['category']}")
            
            if 'page_count' in result['metadata']:
                print(f"  Pages: {result['metadata']['page_count']}")
            
            if 'chunk_id' in result['metadata']:
                print(f"  Chunk ID: {result['metadata']['chunk_id']}")
            
            print("-" * 50)


def main():
    """Main entry point for testing the vector database connector"""
    parser = argparse.ArgumentParser(description='LOKI Vector Database Connector')
    parser.add_argument('--vector-db', type=str, default='/home/mike/LOKI/vector_db',
                        help='Directory containing the vector database')
    parser.add_argument('--query', type=str, required=True,
                        help='Query to test search functionality')
    parser.add_argument('--k', type=int, default=5,
                        help='Number of results to return')
    
    args = parser.parse_args()
    
    try:
        # Initialize the connector
        connector = VectorDBConnector(args.vector_db)
        
        # Test search
        connector.test_search(args.query, args.k)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
