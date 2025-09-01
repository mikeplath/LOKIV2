#!/bin/bash

# LOKI LLM - Localized Offline Knowledge Interface with LLM Integration
# This script runs the LOKI LLM interface for intelligent question answering

# Set paths
LOKI_DIR="/home/mike/LOKI"
LLM_SCRIPT="${LOKI_DIR}/LLM/loki_llm.py"
VECTOR_DB_DIR="${LOKI_DIR}/vector_db"
LOG_DIR="${LOKI_DIR}/logs"
LOG_FILE="${LOG_DIR}/loki_llm_$(date +"%Y-%m-%d_%H-%M-%S").log"
MODELS_DIR="${LOKI_DIR}/LLM/models"

# Make sure directories exist
mkdir -p "${LOG_DIR}"
mkdir -p "${MODELS_DIR}"

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
    
    # Check for llama-cpp-python
    if ! pip list | grep -q "llama-cpp-python"; then
        echo "llama-cpp-python not found. Would you like to install it? (y/n)"
        read -r install_llama
        if [[ $install_llama == "y" ]]; then
            echo "Installing llama-cpp-python... (this may take a while)"
            pip install llama-cpp-python
        else
            echo "Continuing without LLM support. Only vector search will be available."
        fi
    fi
    
    echo "Requirements satisfied."
}

# Display LOKI banner
display_banner() {
    echo "=============================================="
    echo "  LOKI - Localized Offline Knowledge Interface"
    echo "  with LLM Integration"
    echo "=============================================="
    echo "Your offline survival knowledge assistant"
    echo ""
}

# Function to select a model
select_model() {
    # Check if a model path was provided as an argument
    if [ -n "$1" ] && [ -f "$1" ]; then
        echo "Using specified model: $1"
        echo ""
        MODEL_PATH="$1"
        return
    fi
    
    # Look for models in common directories
    echo "Looking for available models..."
    
    # Find all .gguf and .bin files in standard locations
    MODEL_FILES=$(find "$HOME/LOKI/LLM/models" "$HOME/LOKI/models" "$HOME/models" "$HOME/.cache/lm-studio/models" -name "*.gguf" -o -name "*.bin" 2>/dev/null)
    
    # If no models found
    if [ -z "$MODEL_FILES" ]; then
        echo "No models found in standard locations."
        echo "Please enter the path to your model file (.gguf or .bin):"
        read -r MODEL_PATH
        
        if [ ! -f "$MODEL_PATH" ]; then
            echo "ERROR: File not found: $MODEL_PATH"
            echo "Running in search-only mode (no LLM)"
            MODEL_PATH=""
        fi
        return
    fi
    
    # Display available models
    echo "Available models:"
    
    # Convert to array for indexing
    IFS=$'\n' read -r -d '' -a MODEL_ARRAY <<< "$MODEL_FILES"
    
    for i in "${!MODEL_ARRAY[@]}"; do
        echo "$((i+1)): $(basename "${MODEL_ARRAY[$i]}")"
    done
    
    # Option for custom path
    echo "$((${#MODEL_ARRAY[@]}+1)): Enter custom path"
    echo "$((${#MODEL_ARRAY[@]}+2)): Run in search-only mode (no LLM)"
    
    # Get user selection
    echo ""
    echo "Select a model (number):"
    read -r CHOICE
    
    # Process choice
    if [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
        if [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le "${#MODEL_ARRAY[@]}" ]; then
            MODEL_PATH="${MODEL_ARRAY[$((CHOICE-1))]}"
            echo "Selected model: $(basename "$MODEL_PATH")"
        elif [ "$CHOICE" -eq "$((${#MODEL_ARRAY[@]}+1))" ]; then
            echo "Enter path to model file:"
            read -r MODEL_PATH
            if [ ! -f "$MODEL_PATH" ]; then
                echo "ERROR: File not found: $MODEL_PATH"
                echo "Running in search-only mode (no LLM)"
                MODEL_PATH=""
            fi
        elif [ "$CHOICE" -eq "$((${#MODEL_ARRAY[@]}+2))" ]; then
            echo "Running in search-only mode (no LLM)"
            MODEL_PATH=""
        else
            echo "Invalid choice. Running in search-only mode (no LLM)"
            MODEL_PATH=""
        fi
    else
        echo "Invalid input. Running in search-only mode (no LLM)"
        MODEL_PATH=""
    fi
}

# Function to set context window size
set_context_size() {
    DEFAULT_CONTEXT=8192
    
    echo ""
    echo "Enter context window size (default: $DEFAULT_CONTEXT, press Enter to use default):"
    read -r CUSTOM_CONTEXT
    
    if [[ "$CUSTOM_CONTEXT" =~ ^[0-9]+$ ]]; then
        CONTEXT_SIZE=$CUSTOM_CONTEXT
    else
        CONTEXT_SIZE=$DEFAULT_CONTEXT
    fi
    
    echo "Using context size: $CONTEXT_SIZE"
}

# Function to set temperature
set_temperature() {
    DEFAULT_TEMP=0.7
    
    echo ""
    echo "Enter temperature (0.0-1.0, default: $DEFAULT_TEMP, press Enter to use default):"
    read -r CUSTOM_TEMP
    
    if [[ "$CUSTOM_TEMP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$CUSTOM_TEMP <= 1.0" | bc -l) )); then
        TEMPERATURE=$CUSTOM_TEMP
    else
        TEMPERATURE=$DEFAULT_TEMP
    fi
    
    echo "Using temperature: $TEMPERATURE"
}

# Main function
main() {
    display_banner
    
    # Check if the vector database exists
    echo "Checking vector database..."
    check_vector_db
    
    # Install required packages
    install_requirements
    
    # Parse command-line arguments
    MODEL_ARG=""
    QUESTION_ARG=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                MODEL_ARG="$2"
                shift 2
                ;;
            --question)
                QUESTION_ARG="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    # Select model
    select_model "$MODEL_ARG"
    
    # Set context size and temperature if model was selected
    if [ -n "$MODEL_PATH" ]; then
        set_context_size
        set_temperature
    fi
    
    echo "Starting LOKI LLM Interface..."
    echo "Logs will be saved to: ${LOG_FILE}"
    echo ""
    
    # Build command
    CMD="python3 ${LLM_SCRIPT}"
    
    if [ -n "$MODEL_PATH" ]; then
        CMD="${CMD} --model \"${MODEL_PATH}\" --context-size ${CONTEXT_SIZE} --temperature ${TEMPERATURE}"
    fi
    
    if [ -n "$QUESTION_ARG" ]; then
        CMD="${CMD} --question \"${QUESTION_ARG}\""
    fi
    
    # Run the LLM interface
    cd "${LOKI_DIR}"
    eval "${CMD}" 2>&1 | tee -a "${LOG_FILE}"
    
    echo ""
    echo "LOKI LLM session ended."
    echo "Log saved to: ${LOG_FILE}"
}

# Run the main function with all arguments
main "$@"
