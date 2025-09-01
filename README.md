# LOKI - Localized Offline Knowledge Interface

LOKI (Localized Offline Knowledge Interface) is an offline database system with LLM integration, designed to provide access to survival information without requiring an internet connection.

## Features

- Vector database search of survival information
- Integration with local LLM models
- GUI interface with chat-like interaction
- Completely offline operation
- Source document references with clickable links

## Requirements

- Python 3.8+
- Sentence Transformers
- FAISS for vector database
- llama-cpp-python for LLM integration
- CustomTkinter for GUI

## Setup

1. Clone this repository
2. Install required packages:
pip install -r requirements.txt
Code

3. Download a compatible LLM model (GGUF format)
4. Place the model in the LLM/models directory
5. Run the GUI:

python GUI/loki_gui.py
Code


## Note

This repository contains only the code for LOKI. The actual survival library and vector database must be created separately due to their size.

## License

This project is open source and available under the MIT License.
