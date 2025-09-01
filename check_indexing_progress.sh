#!/bin/bash

# LOKI Indexing Progress Checker
# This script will show the current progress of the indexing process

# Define paths
PROGRESS_FILE="/home/mike/LOKI/logs/indexing_progress.txt"
LOG_DIR="/home/mike/LOKI/logs"
INDEXED_DIR="/home/mike/LOKI/indexed_data"
DATABASE_DIR="/home/mike/LOKI/DATABASE/survivorlibrary"

# Print header
echo "==== LOKI Indexing Progress Report ===="
echo "Time: $(date)"
echo ""

# Check if progress file exists and show it
if [ -f "$PROGRESS_FILE" ]; then
    cat "$PROGRESS_FILE"
else
    echo "No progress file found. Indexing may not be running."
    
    # Calculate progress manually
    TOTAL_PDFS=$(find "$DATABASE_DIR" -name "*.pdf" | wc -l)
    INDEXED_FILES=$(find "$INDEXED_DIR" -name "*.json" | wc -l)
    
    echo "Total PDFs in database: $TOTAL_PDFS"
    echo "Indexed files: $INDEXED_FILES"
    
    if [ $TOTAL_PDFS -gt 0 ]; then
        PERCENTAGE=$((INDEXED_FILES * 100 / TOTAL_PDFS))
        echo "Progress: $PERCENTAGE%"
    fi
fi

echo ""
echo "== Recent Log Entries =="

# Find the most recent log file
LATEST_LOG=$(ls -t "$LOG_DIR"/full_indexing_*.log 2>/dev/null | head -1)

if [ -n "$LATEST_LOG" ]; then
    echo "From: $LATEST_LOG"
    echo "---------------------------------"
    tail -n 10 "$LATEST_LOG"
else
    echo "No log files found."
fi

echo ""
echo "== System Status =="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')%"
echo "Memory Usage: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk Usage: $(df -h /home | awk 'NR==2{print $5 " used, " $4 " free"}')"

echo ""
echo "To see more details, use these commands:"
echo "- View full log: less $LATEST_LOG"
echo "- Watch log in real-time: tail -f $LATEST_LOG"
echo "=================================="
