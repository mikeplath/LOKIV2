#!/bin/bash

# LOKI Backup Script
# This script backs up the LOKI project to an SD card

# Set source and destination paths
SOURCE_DIR="/home/mike/LOKI"
BACKUP_DIR="/run/media/mike/1TB SD/LOKI/BACKUP 8.31.25"

# Function to display progress
show_progress() {
  echo "============================"
  echo "$1"
  echo "============================"
}

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  show_progress "ERROR: Source directory $SOURCE_DIR does not exist!"
  echo "Press Enter to exit"
  read
  exit 1
fi

# Check if SD card is mounted
if [ ! -d "/run/media/mike/1TB SD" ]; then
  show_progress "ERROR: SD card not found at /run/media/mike/1TB SD"
  echo "Please make sure your SD card is properly inserted"
  echo "Press Enter to exit"
  read
  exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Display start message
show_progress "Starting backup of LOKI to SD card"
echo "Source: $SOURCE_DIR"
echo "Destination: $BACKUP_DIR"
echo ""

# Copy files with progress display
show_progress "Copying files..."
rsync -ah --info=progress2 "$SOURCE_DIR/" "$BACKUP_DIR/"

# Check if backup was successful
if [ $? -eq 0 ]; then
  show_progress "Backup completed successfully!"
else
  show_progress "ERROR: Backup failed!"
fi

# Create a simple verification report
show_progress "Creating backup verification report..."
SOURCE_SIZE=$(du -sh "$SOURCE_DIR" | cut -f1)
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
TOTAL_FILES_SOURCE=$(find "$SOURCE_DIR" -type f | wc -l)
TOTAL_FILES_BACKUP=$(find "$BACKUP_DIR" -type f | wc -l)

echo "Verification Report:" > "$BACKUP_DIR/backup_report.txt"
echo "Backup Date: $(date)" >> "$BACKUP_DIR/backup_report.txt"
echo "Source Size: $SOURCE_SIZE" >> "$BACKUP_DIR/backup_report.txt"
echo "Backup Size: $BACKUP_SIZE" >> "$BACKUP_DIR/backup_report.txt"
echo "Files in Source: $TOTAL_FILES_SOURCE" >> "$BACKUP_DIR/backup_report.txt"
echo "Files in Backup: $TOTAL_FILES_BACKUP" >> "$BACKUP_DIR/backup_report.txt"

echo ""
echo "Verification Report:"
echo "Source Size: $SOURCE_SIZE"
echo "Backup Size: $BACKUP_SIZE"
echo "Files in Source: $TOTAL_FILES_SOURCE"
echo "Files in Backup: $TOTAL_FILES_BACKUP"

echo ""
echo "Backup complete! Press Enter to exit"
read
