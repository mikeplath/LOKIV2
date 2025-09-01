#!/bin/bash

# LOKI - Localized Offline Knowledge Interface
# This script runs the LOKI search interface

# Set paths
LOKI_DIR="/home/mike/LOKI"
VECTOR_DB_DIR="${LOKI_DIR}/vector_db"
LOG_DIR="${LOKI_DIR}/logs"
LOG_FILE="${LOG_DIR}/loki_search_$(date +"%Y-%m-%d_%H-%M-%S").log"

# Make sure directories exist
mkdir -p "${LOG_DIR}"

# Function to check if the vector database exists
check_vector_db() {
    if [ ! -d "${VECTOR_DB_DIR}" ]; then
        echo "ERROR: Vector database directory not found at ${VECTOR_DB_DIR}"
        echo "Please run the vector database creation script first."
        exit 1
    fi
    
    if [ ! -f "${VECTOR_DB_DIR}/faiss_index.bin" ]; then
        echo "ERROR: FAISS index not found. Vector database may be incomplete."
        echo "Please ensure the vector database creation has completed."
        exit 1
    fi
}

# Function to install required Python packages if not already installed
install_requirements() {
    echo "Checking and installing required Python packages..."
    pip install -q sentence-transformers faiss-cpu rich || {
        echo "ERROR: Failed to install required packages."
        echo "Please try installing them manually with:"
        echo "pip install sentence-transformers faiss-cpu rich"
        exit 1
    }
    echo "Requirements satisfied."
}

# Display LOKI banner
display_banner() {
    echo "=================================="
    echo "  LOKI - Localized Offline"
    echo "  Knowledge Interface"
    echo "=================================="
    echo "Your offline survival knowledge search engine"
    echo ""
}

# Main function
main() {
    display_banner
    
    # Check if the vector database exists
    echo "Checking vector database..."
    check_vector_db
    
    # Install required packages
    install_requirements
    
    echo "Starting LOKI Search Interface..."
    echo "Logs will be saved to: ${LOG_FILE}"
    echo ""
    
    # Run the search interface
    cd "${LOKI_DIR}"
    python3 loki_search.py "$@" 2>&1 | tee -a "${LOG_FILE}"
    
    echo ""
    echo "LOKI search session ended."
    echo "Log saved to: ${LOG_FILE}"
}

# Run the main function
main "$@"
