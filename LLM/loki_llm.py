#!/usr/bin/env python3
"""
LOKI LLM Integration - Localized Offline Knowledge Interface
This script integrates the LOKI vector search with local LLMs for answering questions.
Features real-time text streaming and clickable PDF sources.
"""

import os
import sys
import json
import pickle
import argparse
import time
import re
import textwrap
from datetime import datetime
from pathlib import Path
import subprocess

# Check for required packages and import them
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from rich.live import Live
except ImportError as e:
    print(f"Error: Missing required package: {str(e)}")
    print("Please install required packages with: pip install sentence-transformers faiss-cpu rich")
    sys.exit(1)

# Initialize rich console for pretty output
console = Console()

# Import llama_cpp conditionally, as it might be installed separately
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False


class LokiVectorSearch:
    """LOKI Vector Search Engine for accessing the vector database."""
    
    def __init__(self, vector_db_path="/home/mike/LOKI/vector_db", model_name=None):
        """Initialize the LOKI search engine."""
        self.vector_db_path = vector_db_path
        self.index = None
        self.chunks = None
        self.metadata = None
        self.model = None
        self.model_name = model_name
        self.db_info = None
        self.database_path = "/home/mike/LOKI/DATABASE"
        
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
    
    def get_relevant_chunks_as_context(self, query, top_k=5, min_score=0.5):
        """Get relevant text chunks to use as context for the LLM."""
        search_results = self.search(query, top_k=top_k, min_score=min_score)
        
        # Extract and format the chunks
        context_parts = []
        for i, result in enumerate(search_results.get("results", [])):
            chunk_text = result["chunk"]
            metadata = result["metadata"]
            category = metadata.get("category", "Unknown").replace("library-", "")
            file_name = metadata.get("file_name", "Unknown")
            page_num = metadata.get("page_num", 0)
            similarity = result.get("similarity", 0) * 100  # Convert to percentage
            
            # Format the context with metadata
            context_part = f"[Source {i+1}: {category}/{file_name}, Page {page_num}, Relevance: {similarity:.1f}%]\n{chunk_text}\n"
            context_parts.append(context_part)
        
        # Combine the context parts
        full_context = "\n".join(context_parts)
        
        return {
            "context": full_context,
            "search_results": search_results
        }
    
    def get_file_path(self, metadata):
        """Get the full path to the original PDF file based on metadata."""
        try:
            if not metadata:
                return None
            
            category = metadata.get("category", "").replace("library-", "")
            file_name = metadata.get("file_name", "")
            
            if not category or not file_name:
                return None
            
            # Construct potential file paths
            potential_paths = [
                os.path.join(self.database_path, "survivorlibrary", category, file_name),
                os.path.join(self.database_path, category, file_name),
                os.path.join(self.database_path, file_name)
            ]
            
            # Check if any of the potential paths exist
            for path in potential_paths:
                if os.path.exists(path):
                    return path
            
            return None
        except Exception:
            return None
    
    def open_file(self, metadata):
        """Open the original PDF file at the specified page."""
        file_path = self.get_file_path(metadata)
        if not file_path:
            console.print("[bold red]Error: Could not find the original file.[/bold red]")
            return False
        
        page_num = metadata.get("page_num", 0)
        
        try:
            # Try to use xdg-open to open the PDF
            subprocess.Popen(["xdg-open", file_path])
            return True
        except Exception as e:
            console.print(f"[bold red]Error opening file: {str(e)}[/bold red]")
            return False


class LokiLLM:
    """LOKI LLM Integration for answering questions using local LLM and vector search."""
    
    def __init__(self, 
                 model_path=None, 
                 vector_db_path="/home/mike/LOKI/vector_db", 
                 context_size=8192):
        """Initialize the LOKI LLM interface."""
        self.model_path = model_path
        self.vector_db_path = vector_db_path
        self.context_size = context_size
        self.model = None
        self.search_engine = None
        
        # Validate model path
        if self.model_path and not os.path.exists(self.model_path):
            console.print(f"[bold red]Error: Model file not found at {self.model_path}[/bold red]")
            sys.exit(1)
        
        # Initialize vector search
        self.init_search_engine()
    
    def init_search_engine(self):
        """Initialize the vector search engine."""
        try:
            self.search_engine = LokiVectorSearch(vector_db_path=self.vector_db_path)
        except Exception as e:
            console.print(f"[bold red]Error initializing vector search: {str(e)}[/bold red]")
            sys.exit(1)
    
    def load_model(self):
        """Load the LLM model."""
        if not LLAMA_CPP_AVAILABLE:
            console.print("[bold red]Error: llama_cpp package not installed[/bold red]")
            console.print("Please install it with: pip install llama-cpp-python")
            return False
        
        if not self.model_path:
            console.print("[bold yellow]No model path specified. Using vector search only.[/bold yellow]")
            return False
        
        try:
            console.print(f"[bold blue]Loading LLM model: {os.path.basename(self.model_path)}[/bold blue]")
            console.print("This may take a few moments...")
            
            # Load the model with llama_cpp
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,  # Context window size
                verbose=False  # Set to True for debug information
            )
            
            console.print("[bold green]Model loaded successfully![/bold green]")
            return True
        
        except Exception as e:
            console.print(f"[bold red]Error loading LLM model: {str(e)}[/bold red]")
            return False
    
    def generate_prompt(self, question, context):
        """Generate a prompt for the LLM with the question and context."""
        # Create a prompt that includes the retrieved context
        prompt = f"""
You are LOKI, the Localized Offline Knowledge Interface. You're an AI assistant with access to a vast library of survival knowledge.
Answer the following question based on the information provided in the context.
If the context doesn't contain enough information to answer the question fully, say so and answer to the best of your ability.
For each fact you include in your answer, specify which source (by number) it came from.
Keep your answer focused and to the point without unnecessary repetition.

Context information from the survival library:
{context}

Question: {question}

Answer:
"""
        return prompt
    
    def answer_question_streaming(self, question, top_k=5, min_score=0.5, max_tokens=1024, temperature=0.7):
        """Answer a question using the LLM and vector search with streaming output."""
        # Get relevant context from vector search
        context_data = self.search_engine.get_relevant_chunks_as_context(
            query=question, 
            top_k=top_k, 
            min_score=min_score
        )
        context = context_data["context"]
        search_results = context_data["search_results"]
        
        # Display search information
        console.print(Panel(f"[bold blue]Found {len(search_results.get('results', []))} relevant documents in {search_results.get('search_time', 0):.4f} seconds[/bold blue]"))
        
        # If no context was found
        if not context:
            console.print("[yellow]No relevant information found in the database.[/yellow]")
            return {
                "answer": "I couldn't find any relevant information in my knowledge base to answer your question.",
                "context": "",
                "search_results": search_results
            }
        
        # If LLM is not available or not loaded
        if not LLAMA_CPP_AVAILABLE or not self.model:
            # Just return the context as the answer
            console.print("[yellow]LLM not available. Returning raw search results.[/yellow]")
            
            # Format a simple answer from the search results
            answer = "Here's what I found in the survival library:\n\n"
            for i, result in enumerate(search_results.get("results", [])):
                metadata = result["metadata"]
                category = metadata.get("category", "Unknown").replace("library-", "")
                file_name = metadata.get("file_name", "Unknown")
                
                answer += f"Source {i+1}: {category}/{file_name}\n"
                answer += f"{result['chunk'][:200]}...\n\n"
            
            return {
                "answer": answer,
                "context": context,
                "search_results": search_results
            }
        
        # Generate prompt with context
        prompt = self.generate_prompt(question, context)
        
        try:
            console.print("[bold blue]Generating answer with LLM...[/bold blue]")
            
            # Create a panel to display streaming output
            panel_content = Text("")
            panel = Panel(panel_content, title="LOKI Answer", border_style="green")
            
            # Stream the output
            answer_chunks = []
            
            # Use Live display for updating in real-time
            with Live(panel, refresh_per_second=10) as live:
                # Generate answer with LLM
                for chunk in self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["Question:", "\n\n\n"],
                    stream=True
                ):
                    # Get the text from the chunk
                    chunk_text = chunk["choices"][0]["text"]
                    answer_chunks.append(chunk_text)
                    
                    # Update the displayed text
                    panel_content.append(chunk_text)
                    
                    # Update the live display
                    live.update(panel)
            
            # Combine all chunks into the final answer
            answer = "".join(answer_chunks)
            
            # Clean up any repeated content (common issue with some LLM outputs)
            answer = self.clean_repeated_content(answer)
            
            return {
                "answer": answer,
                "context": context,
                "search_results": search_results,
                "streamed": True  # Mark that this was streamed
            }
            
        except Exception as e:
            console.print(f"[bold red]Error generating answer: {str(e)}[/bold red]")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "context": context,
                "search_results": search_results
            }
    
    def clean_repeated_content(self, text):
        """Remove repetitive content from the generated text."""
        # If the text is short, don't process it
        if len(text) < 500:
            return text
            
        # Split into paragraphs
        paragraphs = re.split(r'\n\n+', text)
        
        # If few paragraphs, return as is
        if len(paragraphs) < 3:
            return text
            
        # Check for repetition in the last third of the text
        start_idx = max(1, len(paragraphs) // 3 * 2)
        unique_paragraphs = []
        
        for i in range(start_idx):
            unique_paragraphs.append(paragraphs[i])
            
        # Add remaining paragraphs only if they're not too similar to earlier ones
        for i in range(start_idx, len(paragraphs)):
            is_repetitive = False
            current = paragraphs[i].strip().lower()
            
            # Skip empty paragraphs
            if not current:
                continue
                
            # Check similarity with previous paragraphs
            for prev in unique_paragraphs[-5:]:  # Compare with the last 5 paragraphs
                prev = prev.strip().lower()
                # If they share significant content
                if len(prev) > 20 and (prev in current or current in prev):
                    is_repetitive = True
                    break
                    
                # Check if there's substantial word overlap (75%+)
                if len(prev) > 50:
                    prev_words = set(prev.split())
                    curr_words = set(current.split())
                    overlap = len(prev_words.intersection(curr_words))
                    if prev_words and overlap / len(prev_words) > 0.75:
                        is_repetitive = True
                        break
            
            if not is_repetitive:
                unique_paragraphs.append(paragraphs[i])
                
        # Recombine the text
        return "\n\n".join(unique_paragraphs)
    
    def display_answer(self, result):
        """Display the answer in a nicely formatted way."""
        answer = result["answer"]
        search_results = result["search_results"]
        
        # Create a title
        console.print()
        console.print(Panel("[bold green]LOKI Answer[/bold green]"))
        
        # Display the answer (we don't need to show it again if it was streamed)
        if "streamed" not in result or not result["streamed"]:
            console.print(Markdown(answer))
        
        # Display source information
        console.print(Panel("[bold blue]Source Information[/bold blue]"))
        
        for i, result in enumerate(search_results.get("results", [])):
            metadata = result["metadata"]
            category = metadata.get("category", "Unknown").replace("library-", "")
            file_name = metadata.get("file_name", "Unknown")
            page_num = metadata.get("page_num", 0)
            similarity = result.get("similarity", 0) * 100  # Convert to percentage
            
            source_table = Table(box=box.SIMPLE, show_header=False)
            source_table.add_column("Key", style="cyan")
            source_table.add_column("Value", style="yellow")
            
            source_table.add_row("Source", f"{i+1}")
            source_table.add_row("Category", category)
            source_table.add_row("File", file_name)
            source_table.add_row("Page", str(page_num))
            source_table.add_row("Relevance", f"{similarity:.1f}%")
            
            console.print(source_table)
            
            # Add option to open the source file
            console.print("[cyan]To open this source file, enter its number.[/cyan]")
            console.print()
    
    def open_source(self, source_num, search_results):
        """Open the source file at the specified page."""
        results = search_results.get("results", [])
        
        if source_num < 1 or source_num > len(results):
            console.print("[bold red]Invalid source number.[/bold red]")
            return False
        
        metadata = results[source_num - 1]["metadata"]
        return self.search_engine.open_file(metadata)
    
    def interactive_session(self, temperature=0.7):
        """Run an interactive Q&A session."""
        console.print(Panel("[bold blue]LOKI Interactive Session[/bold blue]", 
                          subtitle="Type 'exit' to quit, 'help' for assistance"))
        
        # Track the last search results for opening sources
        last_search_results = None
        
        while True:
            # Get question from user
            question = console.input("[bold green]Ask LOKI a question:[/bold green] ")
            question = question.strip()
            
            # Check for exit command
            if question.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting LOKI session.[/yellow]")
                break
            
            # Check for help command
            if question.lower() in ["help", "h", "?"]:
                self.display_help()
                continue
            
            # Check if trying to open a source
            if last_search_results and question.isdigit():
                source_num = int(question)
                if self.open_source(source_num, last_search_results):
                    console.print(f"[green]Opening source {source_num}...[/green]")
                continue
            
            # Check for empty question
            if not question:
                console.print("[yellow]Please enter a question.[/yellow]")
                continue
            
            # Answer the question
            result = self.answer_question_streaming(
                question=question, 
                top_k=5, 
                temperature=temperature,
                max_tokens=2048
            )
            
            # Store search results for source opening
            last_search_results = result["search_results"]
            
            # Mark as streamed so we don't display the answer twice
            result["streamed"] = True
            
            # Display source information
            self.display_answer(result)
    
    def display_help(self):
        """Display help information."""
        help_text = """
# LOKI Help

## Asking Questions
Ask specific questions about survival topics, for example:
- How do I purify water in the wilderness?
- How can I build an emergency shelter?
- What plants are safe to eat in North America?

## Commands
- `exit` or `quit`: Exit the session
- `help`: Display this help information
- Enter a source number to open that source document

## Tips for Better Results
- Be specific in your questions
- Ask one question at a time
- If an answer isn't helpful, try rephrasing your question
        """
        console.print(Markdown(help_text))


def find_models():
    """Find available LLM models in common directories."""
    model_dirs = [
        "/home/mike/LOKI/LLM/models",
        "/home/mike/LOKI/models",
        "/home/mike/models",
        "/home/mike/.cache/lm-studio/models"
    ]
    
    extensions = [".gguf", ".bin"]
    models = []
    
    for directory in model_dirs:
        if not os.path.exists(directory):
            continue
        
        for ext in extensions:
            for model_file in Path(directory).glob(f"**/*{ext}"):
                models.append(str(model_file))
    
    return models


def select_model():
    """Let the user select a model from available options."""
    models = find_models()
    
    if not models:
        console.print("[yellow]No models found in standard locations.[/yellow]")
        model_path = console.input("[bold green]Enter path to your model file (.gguf or .bin):[/bold green] ")
        return model_path if os.path.exists(model_path) else None
    
    # Display available models
    console.print("[bold blue]Available models:[/bold blue]")
    for i, model in enumerate(models):
        console.print(f"[bold]{i+1}[/bold]: {os.path.basename(model)}")
    
    console.print(f"[bold]{len(models)+1}[/bold]: Enter custom path")
    
    # Get user selection
    while True:
        try:
            choice = console.input("[bold green]Select a model (number):[/bold green] ")
            choice = int(choice)
            
            if 1 <= choice <= len(models):
                return models[choice-1]
            elif choice == len(models)+1:
                model_path = console.input("[bold green]Enter path to your model file:[/bold green] ")
                return model_path if os.path.exists(model_path) else None
            else:
                console.print("[yellow]Invalid selection. Try again.[/yellow]")
        
        except ValueError:
            console.print("[yellow]Please enter a number.[/yellow]")


def main():
    """Main function to run the LOKI LLM interface."""
    parser = argparse.ArgumentParser(description="LOKI LLM Interface")
    parser.add_argument("--model", type=str, help="Path to the LLM model file")
    parser.add_argument("--db-path", type=str, default="/home/mike/LOKI/vector_db",
                        help="Path to the vector database directory")
    parser.add_argument("--question", type=str, help="Question to answer (if not provided, runs in interactive mode)")
    parser.add_argument("--context-size", type=int, default=8192, help="Context window size for the LLM")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for LLM generation")
    args = parser.parse_args()
    
    # Create banner
    console.print()
    console.print(Panel.fit(
        Text("LOKI - Localized Offline Knowledge Interface", style="bold blue"),
        subtitle=Text("Your offline survival knowledge assistant", style="italic"),
        border_style="blue"
    ))
    console.print()
    
    # If no model is specified, allow the user to select one
    model_path = args.model
    if not model_path:
        model_path = select_model()
    
    # Initialize the LLM interface
    loki = LokiLLM(
        model_path=model_path,
        vector_db_path=args.db_path,
        context_size=args.context_size
    )
    
    # Load the model if available
    if model_path:
        loki.load_model()
    else:
        console.print("[yellow]No model selected. Running in search-only mode.[/yellow]")
    
    # Run in question or interactive mode
    if args.question:
        # Answer a specific question
        result = loki.answer_question_streaming(
            question=args.question,
            temperature=args.temperature,
            max_tokens=2048
        )
        # Mark as streamed
        result["streamed"] = True
        loki.display_answer(result)
    else:
        # Run interactive mode
        loki.interactive_session(temperature=args.temperature)


if __name__ == "__main__":
    main()
