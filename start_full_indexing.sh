#!/bin/bash

# LOKI Full Indexing Script
# This script will index the entire 200GB Survivor Library
# It includes screen protection, progress tracking, and recovery features

# Create timestamps and directories
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="/home/mike/LOKI/logs/full_indexing_$TIMESTAMP.log"
PROGRESS_FILE="/home/mike/LOKI/logs/indexing_progress.txt"

# Make sure directories exist
mkdir -p /home/mike/LOKI/logs
mkdir -p /home/mike/LOKI/indexed_data

# Function to disable screen blanking
disable_screen_blanking() {
    echo "Disabling screen blanking and power saving..." | tee -a "$LOG_FILE"
    gsettings set org.gnome.desktop.session idle-delay 0
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
    
    echo "Screen blanking disabled. Your screen should stay on during indexing." | tee -a "$LOG_FILE"
    echo "Current idle-delay value: $(gsettings get org.gnome.desktop.session idle-delay)" | tee -a "$LOG_FILE"
    echo "Current power setting: $(gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type)" | tee -a "$LOG_FILE"
}

# Function to restore screen blanking
restore_screen_blanking() {
    echo "Restoring default power settings..." | tee -a "$LOG_FILE"
    gsettings set org.gnome.desktop.session idle-delay 300
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
    echo "Power settings restored." | tee -a "$LOG_FILE"
}

# Function to monitor system resources
monitor_system() {
    while true; do
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        MEM_USAGE=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
        DISK_USAGE=$(df -h /home | awk 'NR==2{print $5}')
        
        echo "$(date +'%Y-%m-%d %H:%M:%S') - CPU: ${CPU_USAGE}% | RAM: ${MEM_USAGE} | Disk: ${DISK_USAGE}" >> "/home/mike/LOKI/logs/system_monitor_$TIMESTAMP.log"
        sleep 60
    done
}

# Function to show an estimate of completion time
show_progress() {
    # Count total number of PDF files
    TOTAL_PDFS=$(find "/home/mike/LOKI/DATABASE/survivorlibrary" -name "*.pdf" | wc -l)
    echo "Total PDFs to process: $TOTAL_PDFS" | tee -a "$LOG_FILE"
    
    # Start time for calculations
    START_TIME=$(date +%s)
    
    # Initial indexed count
    INITIAL_INDEXED=$(find "/home/mike/LOKI/indexed_data" -name "*.json" | wc -l)
    echo "Already indexed before start: $INITIAL_INDEXED files" | tee -a "$LOG_FILE"
    
    while true; do
        # Current indexed count
        CURRENT_INDEXED=$(find "/home/mike/LOKI/indexed_data" -name "*.json" | wc -l)
        NEWLY_INDEXED=$((CURRENT_INDEXED - INITIAL_INDEXED))
        
        # Calculate progress
        if [ $TOTAL_PDFS -gt 0 ]; then
            PERCENTAGE=$((CURRENT_INDEXED * 100 / TOTAL_PDFS))
            
            # Calculate time elapsed and estimate completion
            CURRENT_TIME=$(date +%s)
            ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
            
            if [ $NEWLY_INDEXED -gt 0 ]; then
                # Calculate rate (files per hour)
                RATE=$(echo "scale=2; $NEWLY_INDEXED / ($ELAPSED_TIME / 3600)" | bc)
                
                # Estimate remaining time
                REMAINING_FILES=$((TOTAL_PDFS - CURRENT_INDEXED))
                REMAINING_HOURS=$(echo "scale=1; $REMAINING_FILES / $RATE" | bc 2>/dev/null)
                
                # Format for display
                if [ -n "$REMAINING_HOURS" ] && [ "$REMAINING_HOURS" != "0" ]; then
                    DAYS=$(echo "scale=0; $REMAINING_HOURS/24" | bc)
                    HOURS=$(echo "scale=0; $REMAINING_HOURS%24" | bc)
                    
                    if [ "$DAYS" -gt "0" ]; then
                        REMAINING="$DAYS days, $HOURS hours remaining"
                    else
                        REMAINING="$HOURS hours remaining"
                    fi
                else
                    REMAINING="calculating..."
                fi
                
                # Write to progress file
                echo "Progress: $PERCENTAGE% ($CURRENT_INDEXED/$TOTAL_PDFS files)" > "$PROGRESS_FILE"
                echo "Rate: $RATE files/hour" >> "$PROGRESS_FILE"
                echo "Estimated: $REMAINING" >> "$PROGRESS_FILE"
                echo "Last update: $(date +'%Y-%m-%d %H:%M:%S')" >> "$PROGRESS_FILE"
            else
                echo "Progress: $PERCENTAGE% ($CURRENT_INDEXED/$TOTAL_PDFS files)" > "$PROGRESS_FILE"
                echo "Rate: calculating..." >> "$PROGRESS_FILE"
                echo "Last update: $(date +'%Y-%m-%d %H:%M:%S')" >> "$PROGRESS_FILE"
            fi
        fi
        
        sleep 300  # Update every 5 minutes
    done
}

# Display information about the process
echo "===========================================" | tee -a "$LOG_FILE"
echo "LOKI Full Indexing Process" | tee -a "$LOG_FILE"
echo "Started at $(date)" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"
echo "This process will index your entire 200GB Survivor Library." | tee -a "$LOG_FILE"
echo "Depending on your system, this may take several days." | tee -a "$LOG_FILE"
echo "You can safely press Ctrl+C to stop the process at any time." | tee -a "$LOG_FILE"
echo "When restarted, the process will continue from where it left off." | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Progress file: $PROGRESS_FILE" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"

# Ask for confirmation
echo "Are you ready to start the full indexing process?"
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Ask if OCR should be enabled
echo "Do you want to enable OCR for scanned documents?"
echo "OCR helps with scanned PDFs but is much slower."
echo "Type 'y' for yes or any other key for no:"
read ENABLE_OCR
OCR_FLAG=""
if [[ $ENABLE_OCR == "y" || $ENABLE_OCR == "Y" ]]; then
    OCR_FLAG="--ocr"
    echo "OCR enabled. Processing will be slower but more thorough." | tee -a "$LOG_FILE"
else
    echo "OCR disabled. Processing will be faster but may skip text in scanned documents." | tee -a "$LOG_FILE"
fi

# Ask for number of worker processes
echo "How many worker processes would you like to use?"
echo "More workers = faster processing but higher system load."
echo "Recommended: 1 for systems with 8GB RAM, 2 for 16GB RAM."
echo "Enter a number (1-4):"
read WORKERS
if ! [[ "$WORKERS" =~ ^[1-4]$ ]]; then
    WORKERS=1
    echo "Invalid input. Using 1 worker for safety." | tee -a "$LOG_FILE"
fi
echo "Using $WORKERS worker processes" | tee -a "$LOG_FILE"

# Disable screen blanking
disable_screen_blanking

# Start system monitoring in background
monitor_system &
MONITOR_PID=$!

# Start progress tracking in background
show_progress &
PROGRESS_PID=$!

# Run the indexer with resume capability
echo "Starting indexing process at $(date)" | tee -a "$LOG_FILE"
cd /home/mike/LOKI/indexer

# Use Python to run the indexer
python3 pdf_indexer.py $OCR_FLAG --resume --workers $WORKERS --max-pages 2000 --chunk-size 2000 --chunk-overlap 200 --dpi 150 2>&1 | tee -a "$LOG_FILE"

# Check if the process was interrupted
INDEXING_STATUS=$?
if [ $INDEXING_STATUS -ne 0 ]; then
    echo "Indexing process was interrupted at $(date)" | tee -a "$LOG_FILE"
    echo "You can resume later by running this script again." | tee -a "$LOG_FILE"
else
    echo "Indexing process completed successfully at $(date)" | tee -a "$LOG_FILE"
fi

# Kill background processes
kill $MONITOR_PID 2>/dev/null
kill $PROGRESS_PID 2>/dev/null

# Restore screen blanking
restore_screen_blanking

echo "===========================================" | tee -a "$LOG_FILE"
echo "LOKI Indexing Process Finished at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"

# Display instructions for checking progress
echo ""
echo "To check indexing progress while it's running, open a new terminal and type:"
echo "cat /home/mike/LOKI/logs/indexing_progress.txt"
echo ""
echo "To view the most recent log entries, open a new terminal and type:"
echo "tail -f /home/mike/LOKI/logs/full_indexing_$TIMESTAMP.log"
