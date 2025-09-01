#!/bin/bash

# Disable screen blanking
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'

# Check if the display will stay on
echo "Screen blanking disabled. Your screen should stay on during indexing."
echo "Current idle-delay value: $(gsettings get org.gnome.desktop.session idle-delay)"
echo "Current power setting: $(gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type)"

# Create timestamp for log file
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="/home/mike/LOKI/logs/indexing_$TIMESTAMP.log"

# Start indexing with OCR and parallel processing
echo "Starting indexing process. This will take many hours."
echo "Log file will be written to: $LOG_FILE"
echo "Press Ctrl+C to stop the process if needed."

# Run the indexer
cd /home/mike/LOKI/indexer
python3 pdf_indexer.py --ocr --max-pages 2000 --chunk-size 2000 --chunk-overlap 200 --workers 2 | tee $LOG_FILE

# When finished
echo "Indexing process complete or stopped."
echo "Restoring default power settings."

# Restore default power settings
gsettings set org.gnome.desktop.session idle-delay 300
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
