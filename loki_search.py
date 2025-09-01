#!/usr/bin/env python3
"""
LOKI Search Interface - Localized Offline Knowledge Interface
This script provides a command-line interface for searching the LOKI vector database.
"""

import os
import sys
import json
import pickle
import argparse
import time
from datetime import datetime
import faiss
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Initialize rich console for pretty output
console = Console()

class LokiSearch:
    """LOKI Search Engine for accessing the vector database."""
    
    def __init__(self, vector_db_path="/home/mike/LOKI/vector_db", model_name=None):
        """Initialize the LOKI search engine."""
        self.vector_db_path = vector_db_path
        self.index = None
        self.chunks = None
        self.metadata = None
        self.model = None
        self.model_name = model_name
        self.db_info = None
        
        # Load the database
        self.load_database()
    
    def load_database(self):
        """Load the vector database and associated files."""
        console.print("[bold blue]Loading LOKI Vector Database...[/bold blue]")
        
        try:
            # Check if vector database exists
            if not os.path.exists(self.vector_db_path):
                console.print(f"[bold red]Error: Vector database not found at {self.vector_db_path}[/bold red]")
                console.print("Please run the vector database creation script first.")
                sys.exit(1)
            
            # Load the database info
            info_path = os.path.join(self.vector_db_path, "db_info.json")
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    self.db_info = json.load(f)
                
                # Use the model from the database if not specified
                if self.model_name is None:
                    self.model_name = self.db_info.get("model_name", "all-MiniLM-L6-v2")
            else:
                self.model_name = self.model_name or "all-MiniLM-L6-v2"
            
            # Load the FAISS index
            index_path = os.path.join(self.vector_db_path, "faiss_index.bin")
            if not os.path.exists(index_path):
                console.print(f"[bold red]Error: FAISS index not found at {index_path}[/bold red]")
                sys.exit(1)
            self.index = faiss.read_index(index_path)
            
            # Load the chunks
            chunks_path = os.path.join(self.vector_db_path, "chunks.pkl")
            if not os.path.exists(chunks_path):
                console.print(f"[bold red]Error: Chunks file not found at {chunks_path}[/bold red]")
                sys.exit(1)
            with open(chunks_path, 'rb') as f:
                self.chunks = pickle.load(f)
            
            # Load the metadata
            metadata_path = os.path.join(self.vector_db_path, "metadata.pkl")
            if not os.path.exists(metadata_path):
                console.print(f"[bold red]Error: Metadata file not found at {metadata_path}[/bold red]")
                sys.exit(1)
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            # Load the embedding model
            console.print(f"[yellow]Loading embedding model: {self.model_name}[/yellow]")
            self.model = SentenceTransformer(self.model_name)
            
            # Display database information
            console.print("[bold green]Vector database loaded successfully![/bold green]")
            if self.db_info:
                console.print(f"Creation date: {self.db_info.get('creation_date', 'Unknown')}")
                console.print(f"Total chunks: {self.db_info.get('num_chunks', len(self.chunks))}")
                console.print(f"Total documents: {self.db_info.get('num_documents', 'Unknown')}")
            else:
                console.print(f"Total chunks: {len(self.chunks)}")
            
        except Exception as e:
            console.print(f"[bold red]Error loading vector database: {str(e)}[/bold red]")
            sys.exit(1)
    
    def search(self, query, top_k=5, min_score=0.0):
        """Search the vector database for the given query."""
        try:
            start_time = time.time()
            
            # Encode the query
            query_embedding = self.model.encode([query])[0].reshape(1, -1)
            
            # Search the index
            distances, indices = self.index.search(query_embedding, top_k)
            
            # Process results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    # Calculate similarity score (convert distance to similarity)
                    # FAISS uses L2 distance, so we need to convert to similarity score
                    # Lower distance = higher similarity
                    distance = float(distances[0][i])
                    similarity = 1.0 / (1.0 + distance)
                    
                    # Skip results below minimum score
                    if similarity < min_score:
                        continue
                    
                    result = {
                        "chunk": self.chunks[idx],
                        "metadata": self.metadata[idx],
                        "distance": distance,
                        "similarity": similarity
                    }
                    results.append(result)
            
            # Calculate search time
            search_time = time.time() - start_time
            
            return {
                "results": results,
                "query": query,
                "search_time": search_time,
                "total_results": len(results)
            }
        
        except Exception as e:
            console.print(f"[bold red]Error during search: {str(e)}[/bold red]")
            return {"results": [], "query": query, "error": str(e)}
    
    def display_results(self, search_results):
        """Display the search results in a nicely formatted way."""
        query = search_results["query"]
        results = search_results["results"]
        search_time = search_results.get("search_time", 0)
        total_results = search_results.get("total_results", len(results))
        
        # Create a title
        console.print()
        console.print(Panel(f"[bold blue]LOKI Search Results[/bold blue]", 
                           subtitle=f"Query: '{query}'"))
        console.print()
        
        # Display search stats
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Stat", style="cyan")
        stats_table.add_column("Value", style="yellow")
        stats_table.add_row("Search time", f"{search_time:.4f} seconds")
        stats_table.add_row("Results found", str(total_results))
        stats_table.add_row("Date & time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        console.print(stats_table)
        console.print()
        
        # Display results
        if not results:
            console.print("[bold red]No results found.[/bold red]")
            return
        
        for i, result in enumerate(results):
            # Extract information
            chunk_text = result["chunk"]
            similarity = result.get("similarity", 0) * 100  # Convert to percentage
            metadata = result["metadata"]
            category = metadata.get("category", "Unknown").replace("library-", "")
            file_name = metadata.get("file_name", "Unknown")
            page_num = metadata.get("page_num", 0)
            
            # Format the text
            if len(chunk_text) > 500:
                display_text = chunk_text[:500] + "..."
            else:
                display_text = chunk_text
            
            # Create result panel
            result_title = f"Result #{i+1} - {similarity:.1f}% Match"
            result_panel = Panel(
                display_text,
                title=result_title,
                subtitle=f"Category: {category} | File: {file_name} | Page: {page_num}",
                border_style="green" if similarity > 70 else "yellow" if similarity > 50 else "red"
            )
            console.print(result_panel)
            console.print()
    
    def interactive_search(self):
        """Run an interactive search session."""
        console.print(Panel("[bold blue]LOKI Interactive Search[/bold blue]", 
                          subtitle="Type 'exit' to quit, 'help' for assistance"))
        
        while True:
            # Get query from user
            query = console.input("[bold green]Enter your search query:[/bold green] ")
            query = query.strip()
            
            # Check for exit command
            if query.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting LOKI Search.[/yellow]")
                break
            
            # Check for help command
            if query.lower() in ["help", "h", "?"]:
                self.display_help()
                continue
            
            # Check for empty query
            if not query:
                console.print("[yellow]Please enter a search query.[/yellow]")
                continue
            
            # Perform search
            search_results = self.search(query, top_k=5)
            
            # Display results
            self.display_results(search_results)
    
    def display_help(self):
        """Display help information."""
        help_text = """
# LOKI Search Help

## Basic Search
Simply type your search query and press Enter. For example:
- how to purify water
- treating wounds without antibiotics
- building emergency shelter

## Tips for Better Results
- Be specific in your queries
- Use complete questions or statements
- Try different phrasings if you don't get good results

## Commands
- `exit` or `quit`: Exit the search interface
- `help`: Display this help information
        """
        console.print(Markdown(help_text))


def main():
    """Main function to run the LOKI search interface."""
    parser = argparse.ArgumentParser(description="LOKI Search Interface")
    parser.add_argument("--db-path", type=str, default="/home/mike/LOKI/vector_db",
                        help="Path to the vector database directory")
    parser.add_argument("--model", type=str, default=None,
                        help="Name of the embedding model to use")
    parser.add_argument("--query", type=str,
                        help="Search query (if not provided, runs in interactive mode)")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of results to return")
    args = parser.parse_args()
    
    # Create banner
    console.print()
    console.print(Panel.fit(
        Text("LOKI - Localized Offline Knowledge Interface", style="bold blue"),
        subtitle=Text("Your offline survival knowledge search engine", style="italic"),
        border_style="blue"
    ))
    console.print()
    
    # Initialize the search engine
    loki_search = LokiSearch(vector_db_path=args.db_path, model_name=args.model)
    
    # Run search
    if args.query:
        # Single query mode
        search_results = loki_search.search(args.query, top_k=args.top_k)
        loki_search.display_results(search_results)
    else:
        # Interactive mode
        loki_search.interactive_search()


if __name__ == "__main__":
    main()
