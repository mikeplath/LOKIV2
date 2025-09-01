#!/bin/bash

# LOKI GUI - Graphical User Interface for LOKI
# This script launches the LOKI GUI interface

# Set paths
LOKI_DIR="/home/mike/LOKI"
GUI_SCRIPT="${LOKI_DIR}/GUI/loki_gui.py"
LOG_DIR="${LOKI_DIR}/logs"
LOG_FILE="${LOG_DIR}/loki_gui_$(date +"%Y-%m-%d_%H-%M-%S").log"

# Make sure directories exist
mkdir -p "${LOG_DIR}"

# Function to display banner
display_banner() {
    clear
    echo "=========================================="
    echo "  LOKI - Localized Offline Knowledge Interface"
    echo "  Graphical User Interface"
    echo "=========================================="
    echo "  Your offline survival knowledge assistant"
    echo "=========================================="
    echo ""
}

# Function to check if required packages are installed
check_requirements() {
    echo "Checking required Python packages..."
    
    # Check for tk
    if ! python3 -c "import tkinter" &>/dev/null; then
        echo "Tkinter not found. Installing..."
        sudo dnf install -y python3-tkinter
    fi
    
    # Check for customtkinter and rich
    if ! python3 -c "import customtkinter" &>/dev/null; then
        echo "CustomTkinter not found. Installing..."
        pip install customtkinter
    fi
    
    if ! python3 -c "import rich" &>/dev/null; then
        echo "Rich not found. Installing..."
        pip install rich
    fi
    
    echo "All requirements satisfied."
}

# Function to check vector database
check_vector_db() {
    if [ ! -d "${LOKI_DIR}/vector_db" ]; then
        echo "WARNING: Vector database directory not found!"
        echo "You may need to run the vector database creation script first."
        echo ""
        read -p "Press Enter to continue anyway..."
        return 1
    fi
    
    if [ ! -f "${LOKI_DIR}/vector_db/faiss_index.bin" ]; then
        echo "WARNING: FAISS index not found in vector database!"
        echo "The vector database appears to be incomplete."
        echo ""
        read -p "Press Enter to continue anyway..."
        return 1
    fi
    
    echo "Vector database found."
    return 0
}

# Function to run the GUI
run_gui() {
    echo "Starting LOKI GUI..."
    echo "Log will be saved to: ${LOG_FILE}"
    echo ""
    
    # Run the GUI
    cd "${LOKI_DIR}"
    python3 "${GUI_SCRIPT}" 2>&1 | tee -a "${LOG_FILE}"
    
    # Check exit status
    GUI_STATUS=$?
    if [ $GUI_STATUS -ne 0 ]; then
        echo ""
        echo "ERROR: GUI exited with status $GUI_STATUS"
        echo "Please check the log file for details: ${LOG_FILE}"
        read -p "Press Enter to exit..."
    fi
}

# Main function
main() {
    # Display banner
    display_banner
    
    # Check if GUI script exists
    if [ ! -f "${GUI_SCRIPT}" ]; then
        echo "ERROR: GUI script not found at ${GUI_SCRIPT}"
        echo "Please make sure the LOKI GUI script is properly installed."
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    # Check requirements
    check_requirements
    
    # Check vector database
    check_vector_db
    
    # Run the GUI
    run_gui
}

# Run the main function
main
