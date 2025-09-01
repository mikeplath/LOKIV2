#!/bin/bash

# LOKI - Localized Offline Knowledge Interface
# Launcher script

# Path definitions
LOKI_DIR="/home/mike/LOKI"
GUI_SCRIPT="${LOKI_DIR}/GUI/loki_gui.py"
LOG_DIR="${LOKI_DIR}/logs"
LOG_FILE="${LOG_DIR}/launcher_$(date +"%Y-%m-%d_%H-%M-%S").log"

# Make sure log directory exists
mkdir -p "${LOG_DIR}"

# Log startup
echo "[$(date +"%Y-%m-%d %H:%M:%S")] LOKI Launcher started" > "${LOG_FILE}"

# Check if Python3 and required modules are installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed." | tee -a "${LOG_FILE}"
    zenity --error --title="LOKI Error" --text="Python3 is not installed. Please install it to run LOKI."
    exit 1
fi

# Change to the LOKI directory
cd "${LOKI_DIR}"
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Changed directory to ${LOKI_DIR}" >> "${LOG_FILE}"

# Launch the LOKI GUI
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Launching LOKI GUI" >> "${LOG_FILE}"
python3 "${GUI_SCRIPT}" 2>> "${LOG_FILE}"
EXIT_CODE=$?

# Log exit code
echo "[$(date +"%Y-%m-%d %H:%M:%S")] LOKI GUI exited with code ${EXIT_CODE}" >> "${LOG_FILE}"

# Exit with the same status code as the GUI
exit ${EXIT_CODE}
